"""Bank engine: objectives, rendering, linting rules and blueprint-valid selection."""

from __future__ import annotations

import itertools
from collections import Counter
from pathlib import Path

import pytest

from autorelabel.bank import coverage, lint, render
from autorelabel.bank.loader import Bank, load_blueprint, load_objectives
from autorelabel.bank.model import Check, Task
from autorelabel.bank.select import SelectionError, _matches, generate

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
    ctx = {"user": "natasha", "lab": {"node1": {"ip": "172.25.250.11"}}}
    assert render.render("ssh {{ user }}@{{lab.node1.ip}}", ctx) == "ssh natasha@172.25.250.11"
    with pytest.raises(render.RenderError):
        render.render("{{ missing }}", ctx)
    env = render.env_for({"port": 82}, {"node1": {"ip": "1.2.3.4"}})
    assert env == {"P_PORT": "82", "LAB_NODE1_IP": "1.2.3.4"}


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
