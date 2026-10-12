"""A failing self-test script only fails its own task, unless it is an anchor's."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from autorelabel.bank.model import Task
from autorelabel.engine import EngineError, fresh_checkpoint
from autorelabel.selftest import SelfTest


def _task(tmp_path, tid: str, anchor: str | None = None) -> Task:
    d = tmp_path / tid
    d.mkdir()
    (d / "solution.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    return Task(id=tid, exam="rhcsa", domain="x", path=d, title=tid, primary="p", objectives=(), facets=(),
                difficulty="easy", estimated_minutes=1, node="node1", prompt="", requirements={},
                checks=(), references=(), anchor=anchor)


def _selftest(tasks: dict[str, Task], failing: set[str]) -> SelfTest:
    st = SelfTest.__new__(SelfTest)
    st.bank = SimpleNamespace(tasks=tasks)
    st.lab = SimpleNamespace(facts=lambda: {"node1": {}})
    st._run_on = lambda sess, entry, script, node: (entry["task"] not in failing, "boom")
    return st


def test_failing_task_is_reported_alone(tmp_path):
    tasks = {t: _task(tmp_path, t) for t in ("a", "b", "c")}
    st = _selftest(tasks, failing={"b"})
    who, failed = st._apply(None, [{"task": t} for t in tasks], "solution", 0)
    assert who == ["a", "b", "c"]
    assert set(failed) == {"b"} and "boom" in failed["b"]


def test_failing_anchor_fails_the_round(tmp_path):
    tasks = {"r": _task(tmp_path, "r", anchor="repos"), "a": _task(tmp_path, "a")}
    st = _selftest(tasks, failing={"r"})
    with pytest.raises(EngineError):
        st._apply(None, [{"task": t} for t in tasks], "solution", 0)


def test_tasks_without_a_test_this_round_are_solved(tmp_path):
    tasks = {t: _task(tmp_path, t) for t in ("a", "b")}
    (tasks["a"].path / "tests").mkdir()
    (tasks["a"].path / "tests" / "mistake-x.sh").write_text("#!/usr/bin/env bash\ntrue\n")
    ran: list[str] = []
    st = _selftest(tasks, failing=set())
    st._run_on = lambda sess, entry, script, node: (ran.append(f"{entry['task']}:{script.name}") or True, "")
    who, failed = st._apply(None, [{"task": t} for t in tasks], "mistake", 0)
    assert who == ["a"] and not failed
    assert ran == ["a:mistake-x.sh", "b:solution.sh"]


def test_each_unofficial_grading_gets_its_own_checkpoint(tmp_path):
    first = fresh_checkpoint(tmp_path)
    first.write_text("{}")
    second = fresh_checkpoint(tmp_path)
    assert first != second and not second.exists()


def test_each_provider_keeps_its_own_results(tmp_path, monkeypatch):
    from autorelabel import paths, selftest

    monkeypatch.setattr(paths, "BANKS", tmp_path)
    assert selftest.results_file("rhcsa").name == "selftest.json"
    assert selftest.results_file("rhcsa", "virtualbox").name == "selftest-virtualbox.json"
    task = _task(tmp_path, "t")
    (tmp_path / "rhcsa").mkdir()
    selftest.results_file("rhcsa", "virtualbox").write_text(
        f'{{"t": {{"status": "pass", "digest": "{selftest.task_digest(task)}"}}}}')
    bank = SimpleNamespace(exam="rhcsa", tasks={"t": task})
    assert selftest.verified(bank) == {}
    assert list(selftest.verified(bank, "virtualbox")) == ["t"]
