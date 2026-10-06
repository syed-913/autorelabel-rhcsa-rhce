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
