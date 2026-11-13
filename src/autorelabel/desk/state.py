"""What the Exam Desk's page shows, as plain data: the session's state, the clock, the tasks and
marks, the nodes and their power state, and the result once graded. Built in a worker thread every
second; the parts that don't change during an exam (tasks, nodes) are reused from the previous
snapshot, and the nodes' power state is asked of the hypervisor only every few seconds.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .. import session as S
from ..fsutil import read_json


def snapshot(load_session: Callable[[], S.Session | None], get_engine: Callable[[], Any],
             previous: dict[str, Any], with_nodes: bool = False) -> dict[str, Any]:
    sess = load_session()
    if sess is None:
        return {"open": False}
    out: dict[str, Any] = {
        "open": True, "session": sess.id, "exam": sess.exam, "mode": sess.mode, "state": sess.state,
        "timed": bool(sess.duration_s), "duration": sess.duration_s,
        "remaining": round(sess.remaining()) if sess.duration_s and sess.started else sess.duration_s,
        "marks": dict(sess.marks), "showDifficulty": bool(sess.show_difficulty),
    }
    same = previous.get("session") == sess.id
    eng = get_engine()
    if same and previous.get("tasks"):
        out["tasks"], out["nodes"] = previous["tasks"], previous["nodes"]
    elif eng is not None:
        out["tasks"], out["nodes"] = _tasks(eng, sess), _nodes(eng, sess)
    else:
        out["tasks"], out["nodes"] = [], []
    if eng is not None and (with_nodes or not same):
        _power(eng, sess, out["nodes"])
    health = read_json(sess.dir / "health.json", default={}) or {}
    unreachable = sorted(n for n, h in (health.get("nodes") or {}).items()
                         if isinstance(h, dict) and h.get("grader_access") is False)
    out["unreachable"] = unreachable
    if sess.state == S.GRADED:
        results = read_json(sess.results_file, default={}) or {}
        out["result"] = {"score": results.get("scaled_score"), "passed": bool(results.get("passed")),
                         "passMark": results.get("pass_mark", 210), "total": results.get("total_points", 300)}
    return out


def _tasks(eng: Any, sess: S.Session) -> list[dict[str, Any]]:
    try:
        rendered = eng.rendered(sess)
    except Exception:
        return []
    return [{"number": t["number"], "title": t["title"], "prompt": t["prompt"], "node": t["node"],
             "points": t["points"], "difficulty": t["difficulty"] if sess.show_difficulty else "",
             "consoleOnly": bool(t.get("console_only"))} for t in rendered]


def _nodes(eng: Any, sess: S.Session) -> list[dict[str, Any]]:
    try:
        lab = eng.lab(sess.exam)
        vms = [v for v in lab.vms if v.spec.role != "utility"]
    except Exception:
        return []
    return [{"name": v.name, "fqdn": v.spec.fqdn, "ip": v.lab_ip, "domain": v.domain,
             "user": "student" if sess.exam == "rhce" and v.name == "control" else "root",
             "login": eng.console_login(sess, v.name), "power": "unknown"} for v in vms]


def _power(eng: Any, sess: S.Session, nodes: list[dict[str, Any]]) -> None:
    try:
        lab = eng.lab(sess.exam)
    except Exception:
        return
    for n in nodes:
        try:
            n["power"] = lab.hv.state(n["domain"])[0]
        except Exception:
            n["power"] = "unknown"
