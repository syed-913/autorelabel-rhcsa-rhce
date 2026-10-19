"""Bank engine: objectives, rendering, linting rules and blueprint-valid selection."""

from __future__ import annotations

import datetime
import itertools
import random
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from autorelabel.bank import coverage, lint, render
from autorelabel.bank.loader import Bank, load_blueprint, load_objectives
from autorelabel.bank.model import Check, ParamSpec, Task
from autorelabel.bank.select import SelectionError, _matches, generate, resolve_params, sweep_draws

EXAMS = ("rhcsa", "rhce")


@pytest.mark.parametrize("exam", EXAMS)
def test_objectives_load_and_ids_unique(exam):
    obj = load_objectives(exam)
    ids = [o.id for d in obj.domains for o in d.objectives]
    assert len(ids) == len(set(ids))
    assert all(o.facets for d in obj.domains for o in d.objectives)
    assert all(i.startswith(f"{exam}.") for i in ids)


@pytest.mark.parametrize("exam", EXAMS)
def test_blueprint_arithmetic(exam):
    bp = load_blueprint(exam)
    assert sum(bp.difficulty_mix.values()) == bp.tasks
    assert sum(bp.points[d] * n for d, n in bp.difficulty_mix.items()) == bp.total_points == 300
    assert bp.pass_mark == 210
    lo = sum(v[0] for v in bp.domains.values())
    hi = sum(v[1] for v in bp.domains.values())
    assert lo <= bp.tasks <= hi
    domains = {d.id for d in load_objectives(exam).domains}
    assert set(bp.domains) <= domains


def test_render_strict():
    ctx = {"user": "natasha", "pkgs": ["lsof", "strace"], "lab": {"node1": {"ip": "172.25.250.11"}}}
    assert render.render("ssh {{user}}@{{lab.node1.ip}}", ctx) == "ssh natasha@172.25.250.11"
    assert render.render("{{pkgs.0}} {{pkgs.1}}", ctx) == "lsof strace"
    with pytest.raises(render.RenderError):
        render.render("{{missing}}", ctx)
    with pytest.raises(render.RenderError):
        render.render("{{pkgs.2}}", ctx)
    env = render.env_for({"port": 82, "pkgs": ["a", "b"]}, {"node1": {"ip": "1.2.3.4"}})
    assert env == {"P_PORT": "82", "P_PKGS": "a b", "P_PKGS_0": "a", "P_PKGS_1": "b", "LAB_NODE1_IP": "1.2.3.4"}


def test_render_leaves_jinja_alone():
    # Ansible expressions are written with spaces and must reach the candidate verbatim.
    text = "line: \"{{ item.key }}={{ ansible_facts['hostname'] }}\" for {{user}}"
    assert render.render(text, {"user": "x"}) == "line: \"{{ item.key }}={{ ansible_facts['hostname'] }}\" for x"
    assert render.placeholders(text) == {"user"}


# --- a synthetic bank built from the real RHCSA objectives -------------------------

def _task(obj_id: str, domain: str, n: int, difficulty: str, objectives: Bank, anchor: str | None = None) -> Task:
    o = objectives.objectives.objectives[obj_id]
    return Task(
        id=f"rhcsa.{domain}.t{n}", exam="rhcsa", domain=domain, path=Path("/nonexistent"),
        title=f"task {n}", primary=obj_id, objectives=(obj_id,), facets=(f"{obj_id}:{o.facets[0].id}",),
        difficulty=difficulty, estimated_minutes=5, node="node1", prompt="do it",
        requirements={"R1": "x"}, checks=(Check("c1", "d", "true", ("R1",)),), references=("man x",),
        anchor=anchor, resources={"disk": {"node1.disk1": 600}} if domain == "storage" else {},
    )


@pytest.fixture(scope="module")
def synthetic_bank() -> Bank:
    obj = load_objectives("rhcsa")
    bank = Bank("rhcsa", obj, load_blueprint("rhcsa"), {}, {"usernames": ["a", "b", "c"]})
    diffs = itertools.cycle(["easy", "medium", "hard"])
    n = 0
    for d in obj.domains:
        for o in d.objectives:
            for _ in range(2):
                n += 1
                t = _task(o.id, d.id, n, next(diffs), bank)
                bank.tasks[t.id] = t
    anchors = {"network-node1": ("rhcsa.networking.addresses", "networking", "medium"),
               "repos": ("rhcsa.software.rpm-repos", "software", "easy"),
               "root-reset": ("rhcsa.operate.interrupt-boot", "operate", "hard")}
    for anchor, (oid, dom, diff) in anchors.items():
        n += 1
        t = _task(oid, dom, n, diff, bank, anchor=anchor)
        bank.tasks[t.id] = t
    return bank


def _assert_valid(bank: Bank, exam) -> None:
    bp = bank.blueprint
    assert len(exam) == bp.tasks
    assert sum(s.points for s in exam) == bp.total_points
    diff = Counter(s.task.difficulty for s in exam)
    assert dict(diff) == bp.difficulty_mix
    dom = Counter(s.task.domain for s in exam)
    for d, (lo, hi) in bp.domains.items():
        assert lo <= dom[d] <= hi, (d, dom[d])
    for group in bp.require:
        assert any(_matches(s.task, group) for s in exam), group
    anchors = [s.task.anchor for s in exam if s.task.anchor]
    assert anchors == bp.anchors          # present, once each, in order, first
    assert [s.number for s in exam] == list(range(1, bp.tasks + 1))
    disk = sum(int(s.task.resources.get("disk", {}).get("node1.disk1", 0)) for s in exam)
    assert disk <= 8 * 1024 * 0.9


def test_selection_10k_seeds_always_valid(synthetic_bank):
    for seed in range(10_000):
        _assert_valid(synthetic_bank, generate(synthetic_bank, seed))


def test_selection_is_deterministic(synthetic_bank):
    a = [s.to_json() for s in generate(synthetic_bank, 42)]
    b = [s.to_json() for s in generate(synthetic_bank, 42)]
    assert a == b
    assert a != [s.to_json() for s in generate(synthetic_bank, 43)]


def test_selection_rotates_coverage(synthetic_bank):
    seen = set()
    for seed in range(200):
        seen.update(s.task.primary for s in generate(synthetic_bank, seed))
    assert len(seen) == len(synthetic_bank.objectives.objectives)


def test_selection_reports_too_small_bank():
    bank = Bank("rhcsa", load_objectives("rhcsa"), load_blueprint("rhcsa"), {}, {})
    with pytest.raises(SelectionError):
        generate(bank, 1)


def test_lint_traceability_and_scope(synthetic_bank, tmp_path):
    good = next(iter(synthetic_bank.tasks.values()))
    bad = Task(**{**good.__dict__, "id": "rhcsa.tools.bad", "primary": "rhcsa.tools.nope",
                  "requirements": {"R1": "a", "R2": "b"},
                  "checks": (Check("c1", "d", "true", ("R1",)), Check("c2", "d", "true", ("R9",)))})
    msgs = [i.message for i in lint.lint_task(bad, synthetic_bank) if i.severity == "error"]
    assert any("not an official objective" in m for m in msgs)
    assert any("requirement R2 is not verified" in m for m in msgs)
    assert any("unknown requirement 'R9'" in m for m in msgs)


def test_coverage_gate_levels(synthetic_bank):
    assert coverage.gate_failures(synthetic_bank, "none") == []
    assert coverage.gate_failures(synthetic_bank, "wave1") == []
    full = coverage.gate_failures(synthetic_bank, "full")
    assert any("facet not covered" in f for f in full)   # synthetic tasks only cover the first facet


def test_errexit_hazards_detected():
    script = "test -f a && test -f b\n! grep -q x f\nrc=0; cmd || rc=$?\nout=$(cmd); rc=$?\nfinal\n"
    bad = lint.errexit_hazards(script)
    assert "test -f a && test -f b" in bad
    assert "! grep -q x f" in bad
    assert "out=$(cmd); rc=$?" in bad
    assert not lint.errexit_hazards("cat <<'X'\n! not code\nX\n! last line is fine\n")


def test_early_exit_pipes_detected():
    script = ("rpm -qd x | grep -m1 NEWS\nps | head -1 | cut -c1\nfind / | grep -q y\n"
              "a || head -1 f\nsed -n 1p <<<\"$x\"\ngrep -m1 a <<<\"$x\"\n# x | head\ny | sort  # not | head\n"
              "cat <<'E'\nx | head\nE\n")
    assert lint.early_exit_pipes(script, quiet_grep_ok=False) == [
        "rpm -qd x | grep -m1 NEWS", "ps | head -1 | cut -c1", "find / | grep -q y"]
    assert lint.early_exit_pipes(script, quiet_grep_ok=True) == ["rpm -qd x | grep -m1 NEWS", "ps | head -1 | cut -c1"]


def test_future_dates_are_relative_to_the_exam():
    today = datetime.date(2026, 12, 30)
    task = Task(id="x.y.z", exam="rhcsa", domain="y", path=Path("/nonexistent"), title="t", primary="p",
                objectives=(), facets=(), difficulty="easy", estimated_minutes=1, node="node1", prompt="",
                requirements={}, checks=(), references=(),
                params={"day": ParamSpec("day", "future_date", [20, 30]),
                        "at": ParamSpec("at", "future_date", {"days": [1, 1], "times": ["06:15"]})})
    for seed in range(50):
        (p,) = resolve_params([task], {}, random.Random(seed), today=today)
        assert 20 <= (datetime.date.fromisoformat(p["day"]) - today).days <= 30
        assert p["at"] == "2026-12-31 06:15"


def test_sweep_covers_every_choice_value():
    task = Task(id="x.y.z", exam="rhce", domain="y", path=Path("/nonexistent"), title="t", primary="p",
                objectives=(), facets=(), difficulty="easy", estimated_minutes=1, node="control", prompt="",
                requirements={}, checks=(), references=(),
                params={"a": ParamSpec("a", "choice", [1, 2, 3, 4]), "b": ParamSpec("b", "choice", ["x", "y"]),
                        "n": ParamSpec("n", "range", [5, 9])})
    assert sweep_draws(task) == 4
    drawn = [resolve_params([task], {}, random.Random(i), sweep=i)[0] for i in range(sweep_draws(task))]
    assert [p["a"] for p in drawn] == [1, 2, 3, 4]
    assert [p["b"] for p in drawn] == ["x", "y", "x", "y"]
    assert all(5 <= p["n"] <= 9 for p in drawn)            # other kinds stay random
    assert sweep_draws(replace(task, params={})) == 1


@pytest.mark.parametrize("args,ok", [
    ([20, 300], True), ({"days": [1, 5], "times": ["09:30", "17:45"]}, True),
    ([0, 5], False), ([5], False), ({"days": [1, 5], "times": [1065]}, False),   # unquoted 17:45
    ({"days": [1, 5], "when": ["09:30"]}, False),
])
def test_lint_future_date_args(args, ok, synthetic_bank):
    base = next(iter(synthetic_bank.tasks.values()))
    task = replace(base, params={"d": ParamSpec("d", "future_date", args)})
    msgs = [i.message for i in lint.lint_task(task, synthetic_bank) if "future_date" in i.message]
    assert (not msgs) == ok, msgs


def test_lint_needs_a_check_that_is_not_a_guard(synthetic_bank):
    base = next(iter(synthetic_bank.tasks.values()))
    only_guards = replace(base, checks=tuple(replace(c, guard=True) for c in base.checks))
    msgs = [i.message for i in lint.lint_task(only_guards, synthetic_bank) if i.severity == "error"]
    assert any("every check is a guard" in m for m in msgs)
    assert not [i for i in lint.lint_task(base, synthetic_bank) if "guard" in i.message]
