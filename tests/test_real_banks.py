"""The shipped banks themselves: lint-clean, and every generated exam honours the blueprint."""

from __future__ import annotations

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


@pytest.fixture(scope="module", params=EXAMS)
def bank(request):
    return load_bank(request.param)


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
        assert dict(Counter(t.difficulty for t in tasks)) == bp.difficulty_mix
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
