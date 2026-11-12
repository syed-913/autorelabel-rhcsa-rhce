"""The shipped banks themselves: lint-clean, and every generated exam honours the blueprint."""

from __future__ import annotations

import functools
from collections import Counter

import pytest
import yaml

from autorelabel import labfacts
from autorelabel.bank import load_bank
from autorelabel.bank.lint import lint_bank
from autorelabel.bank.model import Check, Task
from autorelabel.bank.select import _disk_capacity_mib, _matches, generate
from autorelabel.grader import Grader

EXAMS = ("rhcsa", "rhce")
SEEDS = range(2000)


# How often a task may come up across generated exams. A bank is only as varied as its draws: a
# task below the floor is in the bank but practically never in an exam, and one above the
# ceiling is in most of them, so a few exams are enough to know it by heart. Anchors (in every
# exam by design) and practice-only tasks don't count.
DRAW_FLOOR = 0.03
DRAW_CEILING = 0.50


@pytest.fixture(scope="module", params=EXAMS)
def bank(request):
    return load_bank(request.param)


@functools.cache
def draw_shares(exam: str) -> dict[str, float]:
    """task id -> share of the generated exams (no history) that contain it."""
    bank = load_bank(exam)
    seen = Counter(s.task.id for seed in SEEDS for s in generate(bank, seed))
    return {t.id: seen[t.id] / len(SEEDS) for t in bank.tasks.values() if not t.anchor and not t.practice_only}


def _listed(shares: dict[str, float]) -> str:
    return ", ".join(f"{tid.split('.', 1)[1]} {share:.1%}" for tid, share in sorted(shares.items(), key=lambda x: x[1]))


# The floor holds since the generator looks ahead and the blueprints leave it room (1.2.0).
# 2026-11-12, 2,000 seeds: the rarest RHCSA task is in 4.2% of exams (operate.tuned-profile), the
# rarest RHCE task in 7.6% (core.multi-play). Before, 7 RHCSA tasks were in under 1%.
@pytest.mark.parametrize("exam", EXAMS)
def test_no_exam_task_is_practically_never_drawn(exam):
    rare = {tid: s for tid, s in draw_shares(exam).items() if s < DRAW_FLOOR}
    assert not rare, f"drawn in under {DRAW_FLOOR:.0%} of exams: {_listed(rare)}"


# The ceiling does not hold, and no generator can make it: there are too few tasks.
# 2026-11-12, 2,000 seeds. RHCSA: 1 task above 50%, storage.lvm-create at 74%, the only hard
# storage task (10 hard tasks for 4 to 6 hard slots). RHCE: 8 above 50%, content.vault-users at
# 79%: 51 tasks for 16 slots, so the average task is in 31% of exams whatever is done.
# Strict: when new tasks bring a bank under the ceiling, its mark must go.
_TOO_FEW_TASKS = pytest.mark.xfail(strict=True, reason="too few tasks: RHCSA 1 above 50% (74%), RHCE 8 (79%)")


@pytest.mark.parametrize("exam", [pytest.param(e, marks=_TOO_FEW_TASKS) for e in EXAMS])
def test_no_task_is_in_most_exams(exam):
    common = {tid: s for tid, s in draw_shares(exam).items() if s > DRAW_CEILING}
    assert not common, f"drawn in over {DRAW_CEILING:.0%} of exams: {_listed(common)}"


@pytest.mark.parametrize("exam", EXAMS)
def test_the_most_frequent_task_does_not_creep_up(exam):
    """The ceiling test above is a known failure; this one keeps the number from getting worse."""
    worst = {"rhcsa": 0.78, "rhce": 0.83}[exam]      # measured 74% and 79%
    common = {tid: s for tid, s in draw_shares(exam).items() if s > worst}
    assert not common, f"drawn in over {worst:.0%} of exams: {_listed(common)}"


def test_every_difficulty_mix_comes_up(bank):
    mixes = Counter(tuple(sorted(Counter(s.task.difficulty for s in generate(bank, seed)).items()))
                    for seed in range(1, 301))
    assert set(mixes) == {tuple(sorted(m.items())) for m in bank.blueprint.difficulty_mixes}
    assert min(mixes.values()) >= 50, mixes


def test_the_next_exam_is_not_the_last_one_again(bank):
    """One candidate, 60 exams in a row, each knowing the two before it."""
    from autorelabel.bank.select import seen_factors

    free = bank.blueprint.tasks - len(bank.blueprint.anchors)

    def repeats(with_history: bool) -> float:
        earlier: list[list[str]] = []
        counts = []
        for i in range(60):
            seen = seen_factors(earlier[:2]) if with_history else None
            exam = [s.task.id for s in generate(bank, 5000 + i, None, seen) if not s.task.anchor]
            if earlier:
                counts.append(len(set(exam) & set(earlier[0])))
            earlier.insert(0, exam)
        return sum(counts) / len(counts)

    without, held_back = repeats(False), repeats(True)
    # measured over 400 exams: RHCSA 4.5 -> 1.8 of 17, RHCE 6.3 -> 3.4 of 16
    assert held_back < without * 0.7, (without, held_back)
    assert held_back < free * 0.3, held_back


def test_bank_lints_clean(bank):
    errors = [i for i in lint_bank(bank) if i.severity == "error"]
    assert not errors, "\n".join(map(str, errors))


def test_generated_exams_follow_the_blueprint(bank):
    bp = bank.blueprint
    cap = _disk_capacity_mib(bank.exam)
    for seed in SEEDS:
        exam = generate(bank, seed)
        tasks = [s.task for s in exam]
        assert len(exam) == bp.tasks
        assert sum(s.points for s in exam) == bp.total_points
        assert dict(Counter(t.difficulty for t in tasks)) in bp.difficulty_mixes, seed
        dom = Counter(t.domain for t in tasks)
        for d, (lo, hi) in bp.domains.items():
            assert lo <= dom[d] <= hi, (seed, d, dom[d])
        for group in bp.require:
            assert any(_matches(t, group) for t in tasks), (seed, group)
        assert [t.anchor for t in tasks if t.anchor] == bp.anchors, seed
        assert not any(t.practice_only for t in tasks), seed
        excl = [e for t in tasks for e in t.exclusive]
        assert len(excl) == len(set(excl)), (seed, excl)
        disk: Counter[str] = Counter()
        for t in tasks:
            for d, mib in (t.resources.get("disk") or {}).items():
                disk[d] += int(mib)
        assert all(v <= cap.get(d, 0) for d, v in disk.items()), (seed, disk)
        pooled = [(t.params[n].args, v) for s in exam for t in [s.task]
                  for n, v in s.params.items() if t.params[n].kind == "pool"]
        assert len(pooled) == len(set(pooled)), (seed, pooled)


# --- RHCE inventory groups and group-targeted checks ----------------------------------------------

@pytest.mark.parametrize("profile,dev,prod,balancers", [
    ("standard", ["node1"], ["node3", "node4"], ["node5"]),
    ("lite", ["node1"], ["node3"], ["node2"]),
])
def test_rhce_groups(profile, dev, prod, balancers):
    f = labfacts.sample("rhce", profile)
    assert f["groups"]["dev"].split() == dev
    assert f["groups"]["prod"].split() == prod
    assert f["groups"]["webservers"] == f["groups"]["prod"]
    assert f["groups"]["balancers"].split() == balancers
    assert labfacts.check_nodes("@prod", "control", f) == prod
    assert labfacts.check_nodes(None, "control", f) == ["control"]
    assert labfacts.script_nodes("all", f) == f["groups"]["all"].split()
    assert labfacts.script_nodes("node2", f) == ["node2"]
    for g, hosts in f["groups"].items():
        assert all(h in f for h in hosts.split()), (g, hosts)


def test_group_checks_split_their_weight(tmp_path):
    g = Grader.__new__(Grader)                     # only the expansion logic is under test
    g.facts = labfacts.sample("rhce", "standard")
    task = Task(id="rhce.x.y", exam="rhce", domain="x", path=tmp_path, title="t", primary="p",
                objectives=(), facets=(), difficulty="easy", estimated_minutes=1, node="control",
                prompt="", requirements={"R1": ""}, references=(),
                checks=(Check("a", "on prod", "true", ("R1",), on="@prod", weight=2.0),
                        Check("b", "on control", "true", ("R1",))))
    jobs = g._expanded(task)
    assert [(c.id, n) for c, n in jobs] == [("a@node3", "node3"), ("a@node4", "node4"), ("b", "control")]
    assert [c.weight for c, _ in jobs] == [1.0, 1.0, 1.0]


def test_check_targets_survive_yaml(bank):
    # YAML 1.1 reads the key `on` as the boolean True; every `on:` a task writes must reach the model.
    for task in bank.tasks.values():
        raw = yaml.safe_load((task.path / "task.yaml").read_text())
        written = [c.get(True) for c in raw.get("checks", [])]
        assert [c.on for c in task.checks] == written, task.id


def test_package_choices_never_overlap_between_tasks(bank):
    """Two tasks of one exam must not draw the same package: one task's check that a package is
    absent (or present) would then depend on the other task. RHCE's conditional-play once drew
    zip while vars-files installed zip on the same host."""
    owners: dict[str, str] = {}
    for task in bank.tasks.values():
        for name, spec in task.params.items():
            if spec.kind != "choice" or not name.startswith(("pkg", "remove")):
                continue
            for value in spec.args:
                for pkg in (value if isinstance(value, list) else str(value).split()):
                    assert owners.setdefault(pkg, task.id) == task.id, \
                        f"{pkg} is a choice of both {owners[pkg]} and {task.id}"


def test_root_passwords_are_given_unless_a_task_resets_them(tmp_path, monkeypatch):
    """The instructions give every node's root password except where a task resets it."""
    from autorelabel import config, paths
    from autorelabel.engine import Engine

    monkeypatch.setattr(paths, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(paths, "SESSIONS", tmp_path / "sessions")
    monkeypatch.setenv("VBOX_USER_HOME", "")
    config.save(config.Settings(provider="libvirt", storage_dir=str(tmp_path), iso_path=str(tmp_path / "x.iso")))
    eng = Engine()
    exam = eng.create("rhcsa", seed=7)                  # every exam resets node2's root password
    assert sorted(exam.given) == ["node1"]
    assert "password: " + exam.given["node1"] in eng.console_login(exam, "node1")
    assert "not given" in eng.console_login(exam, "node2")
    expired = eng.create("rhcsa", mode="practice", task_ids=["rhcsa.operate.root-account-expired"], seed=7)
    assert sorted(expired.given) == ["node2"]


def test_a_task_whose_test_wipes_a_disk_is_self_tested_alone():
    """gpt-partitions' mistake test writes a new partition table to node2's disk: in one batch
    with swap-partition and vg-extend, their tests then found their partitions gone."""
    from autorelabel.selftest import plan_batches

    bank = load_bank("rhcsa")
    names = ["storage.gpt-partitions", "storage.swap-partition", "storage.vg-extend", "tools.archive-gzip-extract"]
    batches = plan_batches(bank, [bank.tasks[f"rhcsa.{n}"] for n in names])
    assert sorted(sorted(t.id.split(".", 1)[1] for t in b) for b in batches) == [
        ["storage.gpt-partitions"], ["storage.swap-partition", "storage.vg-extend", "tools.archive-gzip-extract"]]
