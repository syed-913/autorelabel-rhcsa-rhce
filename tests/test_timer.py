"""The standalone exam timer (./autorelabel exam timer)."""

from __future__ import annotations

import time

import pytest

from autorelabel import paths, timer
from autorelabel import session as S


@pytest.fixture()
def sess(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SESSIONS", tmp_path)
    s = S.Session(id="t1", exam="rhce", mode="exam", seed=1, created=time.time(), duration_s=4 * 3600)
    s.save()
    return s


def test_big_digits_are_five_rows_and_fit_80_columns():
    rows = timer.big("3:59:59")
    assert len(rows) == 5 and len({len(r) for r in rows}) == 1 and len(rows[0]) <= 80


def test_status_follows_the_session(sess):
    sess.forgive_downtime = False
    sess.state = S.READY
    assert timer.status_line(sess) == ("4:00:00", "not started yet")
    sess.state, sess.started = S.IN_PROGRESS, 1000.0
    text, note = timer.status_line(sess, now=1000.0 + 3600 + 61)
    assert text == "2:58:59" and note.startswith("ends about ")
    sess.state = S.LOCKED
    assert timer.status_line(sess) == ("0:00:00", "time is up: the exam is locked")
    sess.state = S.GRADED
    assert timer.status_line(sess)[1].endswith("and graded")
    sess.duration_s = 0
    assert timer.status_line(sess) == ("untimed", "practice")


def test_timer_ends_when_the_exam_is_over(sess, capsys):
    sess.state, sess.started = S.GRADED, 1000.0
    sess.save()
    assert timer.run("t1") == 0                     # returns at once, no tty: one plain line
    assert "RHCE EXAM  0:00:00  time is up" in capsys.readouterr().out


def test_once_prints_just_the_time(sess, capsys):
    sess.state, sess.started, sess.forgive_downtime = S.IN_PROGRESS, time.time() - 60, False
    timer.once(sess)
    assert capsys.readouterr().out.strip() in ("3:59:00", "3:58:59")
