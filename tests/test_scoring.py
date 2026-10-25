"""Partial-credit scoring: guard checks (things not to break) only score once the task's own
work does, so an untouched exam scores nothing."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from autorelabel.bank.model import Check, Task
from autorelabel.grader import Grader


def _task(tmp_path, checks: list[Check]) -> Task:
    return Task(id="rhcsa.x.t", exam="rhcsa", domain="x", path=tmp_path, title="T", primary="p",
                objectives=(), facets=(), difficulty="easy", estimated_minutes=5, node="node1", prompt="",
                requirements={"R1": "r"}, checks=tuple(checks), references=())


def _results(tmp_path, statuses: dict[str, str], scoring: str = "partial") -> dict:
    checks = [Check("work", "the work", "true", ("R1",)),
              Check("more", "more work", "true", ("R1",)),
              Check("keep", "SELinux stays enforcing", "true", ("R1",), guard=True)]
    task = _task(tmp_path, checks)
    g = Grader.__new__(Grader)
    g.bank = SimpleNamespace(tasks={task.id: task}, blueprint=SimpleNamespace(total_points=30, pass_mark=21))
    g.facts = {}
    g.s = SimpleNamespace(id="s", exam="rhcsa", mode="exam", scoring=scoring, incidents=[], duration_s=0,
                          elapsed=lambda: 0, tasks=[{"number": 1, "task": task.id, "params": {}, "points": 30}])
    g._expanded = lambda t: [(c, "node1") for c in t.checks]
    post = {f"1:{c.id}": {"id": c.id, "desc": c.desc, "node": "node1", "status": statuses[c.id],
                          "weight": 1.0, "covers": ["R1"], "detail": "", "guard": c.guard} for c in checks}
    return g.score({"post": post})


def _score(tmp_path, statuses: dict[str, str], scoring: str = "partial") -> float:
    return _results(tmp_path, statuses, scoring)["tasks"][0]["points"]


def test_possible_points_stay_whole_numbers(tmp_path):
    r = _results(tmp_path, {"work": "pass", "more": "fail", "keep": "pass"})
    for v in (r["by_difficulty"]["easy"], r["by_domain"]["x"]):
        assert v["possible"] == 30 and isinstance(v["possible"], int)     # shown as 20/30, not 20/30.0


@pytest.mark.parametrize("statuses, points", [
    ({"work": "fail", "more": "fail", "keep": "pass"}, 0),        # untouched: the guard alone scores nothing
    ({"work": "pass", "more": "fail", "keep": "pass"}, 20),       # work started: the guard counts again
    ({"work": "pass", "more": "pass", "keep": "fail"}, 20),       # broke what it had to keep: points lost
    ({"work": "pass", "more": "pass", "keep": "pass"}, 30),
])
def test_guards_only_score_with_the_work(tmp_path, statuses, points):
    assert _score(tmp_path, statuses) == points


def test_strict_scoring_is_unchanged(tmp_path):
    assert _score(tmp_path, {"work": "pass", "more": "pass", "keep": "pass"}, "strict") == 30
    assert _score(tmp_path, {"work": "pass", "more": "pass", "keep": "fail"}, "strict") == 0


def _score_hosts(tmp_path, statuses: dict[str, str]) -> float:
    """One check on a group of three hosts (weight shared) plus one single-host check."""
    checks = [Check("role", "role file", "true", ("R1",)), Check("other", "other work", "true", ("R1",))]
    task = _task(tmp_path, checks)
    g = Grader.__new__(Grader)
    g.bank = SimpleNamespace(tasks={task.id: task}, blueprint=SimpleNamespace(total_points=30, pass_mark=21))
    g.facts = {}
    g.s = SimpleNamespace(id="s", exam="rhce", mode="exam", scoring="partial", incidents=[], duration_s=0,
                          elapsed=lambda: 0, tasks=[{"number": 1, "task": task.id, "params": {}, "points": 30}])
    expanded = [(Check(f"role@{h}", "role file", "true", ("R1",), weight=1 / 3), h)
                for h in ("node1", "node2", "node3")] + [(checks[1], "node1")]
    g._expanded = lambda t: expanded
    post = {f"1:{c.id}": {"id": c.id, "desc": c.desc, "node": n, "status": statuses[c.id], "weight": c.weight,
                          "covers": ["R1"], "detail": "", "guard": False} for c, n in expanded}
    return g.score({"post": post})["tasks"][0]["points"]


@pytest.mark.parametrize("statuses, points", [
    # untouched: the host the check doesn't apply to (n/a) earns nothing
    ({"role@node1": "fail", "role@node2": "n/a", "role@node3": "fail", "other": "fail"}, 0),
    # the two applicable hosts share the check's whole weight: one of them right = a quarter
    ({"role@node1": "pass", "role@node2": "n/a", "role@node3": "fail", "other": "fail"}, 7.5),
    ({"role@node1": "pass", "role@node2": "n/a", "role@node3": "pass", "other": "pass"}, 30),
    # applies nowhere: the task is scored on its other checks alone
    ({"role@node1": "n/a", "role@node2": "n/a", "role@node3": "n/a", "other": "pass"}, 30),
])
def test_checks_that_do_not_apply_to_a_host(tmp_path, statuses, points):
    assert _score_hosts(tmp_path, statuses) == points
