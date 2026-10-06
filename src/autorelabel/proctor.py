"""The proctor: a background process (transient systemd --user unit) that keeps
time, sends warnings, watches lab health, locks the exam at zero and grades it.
It keeps running when the TUI is closed and stops itself when the exam ends."""

from __future__ import annotations

import json
import shutil
import time
from typing import Any

from . import log, proc, remote
from . import session as S
from .engine import Engine
from .fsutil import LockBusy, atomic_write_json, file_lock
from .providers import libvirt as lv

_log = log.get("proctor")
HEALTH_EVERY = 120


def _notify(title: str, body: str) -> None:
    if shutil.which("notify-send"):
        proc.run(["notify-send", "-a", "autorelabel", "-u", "critical", title, body], timeout=10)


def _wall(engine: Engine, sess: S.Session, message: str) -> None:
    lab = engine.lab(sess.exam)
    for v in lab.vms:
        if v.spec.role == "utility" or v.name in sess.broken_nodes:
            continue
        remote.run_cmd(lab.target(v.name), f"wall -n {json.dumps(message)} 2>/dev/null || wall {json.dumps(message)}",
                       timeout=15)


def _health(engine: Engine, sess: S.Session) -> dict[str, Any]:
    """Can the grader still reach each node? (warns the candidate early)."""
    lab = engine.lab(sess.exam)
    out: dict[str, Any] = {"checked": time.time(), "nodes": {}}
    for v in lab.vms:
        if v.spec.role == "utility":
            continue
        st, reason = lv.state(v.domain)
        entry = {"state": st, "reason": reason, "grader_access": None}
        if st == "running" and v.name not in sess.broken_nodes:
            t = lab.target(v.name)
            ok = remote.reachable(t, timeout=15)
            if ok:
                ok = remote.run_cmd(t, "true", timeout=15).ok      # sudo still works?
            entry["grader_access"] = ok
        out["nodes"][v.name] = entry
    atomic_write_json(sess.dir / "health.json", out)
    return out


def run(session_id: str) -> int:
    log.setup()
    sess = S.load(session_id)
    try:
        with file_lock(sess.lock_file):
            return _loop(session_id)
    except LockBusy:
        _log.info("another proctor already runs for %s", session_id)
        return 0


def _loop(session_id: str) -> int:
    engine = Engine()
    last_health = 0.0
    warned_access: set[str] = set()
    while True:
        sess = S.load(session_id)
        if sess.state in (S.LOCKED, S.GRADING_INTERRUPTED, S.GRADING):
            return _grade(engine, sess)
        if sess.state != S.IN_PROGRESS:
            _log.info("session %s is %s; proctor exits", session_id, sess.state)
            return 0
        sess.tick()
        remaining = sess.remaining()
        fired = sess.fired_warnings()
        for minutes in sorted(sess.warnings_minutes, reverse=True):
            if minutes not in fired and remaining <= minutes * 60 and remaining > 0:
                sess.mark_warning(minutes)
                msg = f"autorelabel: {minutes} minute{'s' if minutes != 1 else ''} left in your exam."
                sess.event("warning", minutes=minutes)
                _wall(engine, sess, msg)
                _notify("autorelabel", msg)
        if remaining <= 0:
            _wall(engine, sess, "autorelabel: time is up. The exam is now locked for grading.")
            _notify("autorelabel", "Time is up. Your exam is locked and being graded.")
            engine.lock(sess, reason="time")
            continue
        if time.time() - last_health > HEALTH_EVERY:
            last_health = time.time()
            try:
                health = _health(engine, sess)
                for node, h in health["nodes"].items():
                    if h["grader_access"] is False and node not in warned_access:
                        warned_access.add(node)
                        sess.incident(node, "grader-access", "the grader cannot log in (mgmt0, the vagrant "
                                                             "account, sshd or sudo was changed)")
                        _wall(engine, sess, f"autorelabel WARNING: the grader can no longer reach {node}. "
                                            "Revert changes to mgmt0 / the vagrant account / sshd, or "
                                            f"{node} will score 0.")
                    elif h["grader_access"]:
                        warned_access.discard(node)
            except Exception:  # health is advisory; never kill the proctor
                _log.exception("health check failed")
        time.sleep(S.HEARTBEAT_INTERVAL)


def _grade(engine: Engine, sess: S.Session) -> int:
    progress = sess.dir / "grading-progress.json"

    def on_event(kind: str, data: dict[str, Any]) -> None:
        atomic_write_json(progress, {"ts": time.time(), "kind": kind, **data})

    try:
        engine.grade(sess, on_event)
    except Exception as exc:
        _log.exception("grading failed")
        atomic_write_json(progress, {"ts": time.time(), "kind": "error", "message": str(exc)})
        return 1
    atomic_write_json(progress, {"ts": time.time(), "kind": "done"})
    return 0
