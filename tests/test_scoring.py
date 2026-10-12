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


def _score(tmp_path, statuses: dict[str, str], scoring: str = "partial") -> float:
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
    return g.score({"post": post})["tasks"][0]["points"]


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
