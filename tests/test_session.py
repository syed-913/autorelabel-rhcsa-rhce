"""Session state machine, journal and crash-forgiving timekeeping."""

from __future__ import annotations

import json
import time

import pytest

from autorelabel import paths
from autorelabel import session as S


@pytest.fixture()
def sess(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SESSIONS", tmp_path)
    s = S.Session(id="t1", exam="rhcsa", mode="exam", seed=1, created=time.time(), duration_s=600)
    s.save()
    return s


def test_transitions_and_journal(sess):
    sess.transition(S.PROVISIONING)
    sess.transition(S.READY)
    with pytest.raises(S.SessionError):
        sess.transition(S.GRADED)
    sess.incident("node1", "forced-reset", "was reset")          # 'kind' must not collide
    events = [json.loads(line) for line in sess.journal.read_text().splitlines()]
    assert [e["event"] for e in events] == ["state", "state", "incident"]
    assert events[-1]["kind"] == "forced-reset"
    assert S.load("t1").state == S.READY


def test_tick_counts_small_steps_and_forgives_gaps(sess, monkeypatch):
    sess.started = 1000.0
    sess.state = S.IN_PROGRESS
    monkeypatch.setattr(S, "boot_id", lambda: "boot-A")
    sess.tick(now=1000.0)
    sess.tick(now=1005.0)
    sess.tick(now=1010.0)
    assert sess.heartbeat()["elapsed"] == pytest.approx(10.0)
    sess.tick(now=1310.0)                          # 5 min gap (suspend): forgiven
    assert sess.heartbeat()["elapsed"] == pytest.approx(10.0)
    monkeypatch.setattr(S, "boot_id", lambda: "boot-B")
    sess.tick(now=5000.0)                          # host rebooted: forgiven
    assert sess.heartbeat()["elapsed"] == pytest.approx(10.0)
    assert sess.remaining(now=5000.0) == pytest.approx(590.0, abs=0.5)


def test_strict_wall_clock(sess):
    sess.forgive_downtime = False
    sess.started = 1000.0
    sess.state = S.IN_PROGRESS
    assert sess.elapsed(now=1300.0) == 300.0
    assert sess.remaining(now=2000.0) == 0.0


def test_journal_rebuild(sess):
    sess.transition(S.PROVISIONING)
    sess.transition(S.READY)
    assert S.rebuild_from_journal("t1") == S.READY


def test_exam_start_refuses_to_replace_an_open_session(tmp_path, monkeypatch, capsys):
    import argparse

    from autorelabel import commands, paths
    from autorelabel import session as S

    monkeypatch.setattr(paths, "SESSIONS", tmp_path)
    open_exam = S.Session(id="20260101-000000-aaaaaa", exam="rhcsa", mode="exam", seed=1, created=0.0,
                          state=S.IN_PROGRESS)
    open_exam.save()
    S.set_current(open_exam)
    args = argparse.Namespace(exam="rhce", seed=None, no_start=False, verbose=False)
    assert commands.cmd_exam_start(args) == 1
    assert "still open" in capsys.readouterr().err
    assert S.current().id == open_exam.id


def test_two_copies_of_a_session_do_not_undo_each_other(sess):
    """The proctor and the TUI each load the session and save later."""
    sess.transition(S.PROVISIONING)
    sess.transition(S.READY)
    sess.transition(S.IN_PROGRESS)
    proctor, tui = S.load("t1"), S.load("t1")

    tui.marks["3"] = "done"
    tui.save()
    proctor.incident("node2", "grader-access", "cannot log in")          # saved from the older copy
    on_disk = S.load("t1")
    assert on_disk.marks == {"3": "done"}
    assert [i["kind"] for i in on_disk.incidents] == ["grader-access"]
    assert proctor.marks == {"3": "done"}                                 # and the copy caught up

    proctor.transition(S.LOCKED, reason="time")
    tui.marks["5"] = "flag"                                               # still thinks: in progress
    del tui.marks["3"]
    tui.incident("node1", "reset-to-start", "reset by the candidate")
    on_disk = S.load("t1")
    assert on_disk.state == S.LOCKED and tui.state == S.LOCKED
    assert on_disk.marks == {"5": "flag"}
    assert [i["kind"] for i in on_disk.incidents] == ["grader-access", "reset-to-start"]


def test_a_new_session_and_a_changed_field_are_saved_whole(sess):
    sess.started = 1234.0
    sess.code_port = 18081
    sess.save()
    again = S.load("t1")
    assert (again.started, again.code_port) == (1234.0, 18081)
    assert oct(again.file.stat().st_mode & 0o777) == "0o600"
