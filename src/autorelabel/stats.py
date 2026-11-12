"""What the graded attempts say, read from the files autorelabel already keeps: one line per
attempt in history.jsonl, and each session's results.json for the checks. Read-only.

Plain data out, no HTML and no HTTP: the results dashboard renders it, and anything else that
wants the same numbers can call the same functions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import paths

SESSION_ID = re.compile(r"[0-9A-Za-z_-]{1,64}\Z")     # used with match(): the whole id, no trailing newline
RECENT = 5          # an objective's or a task's number is the mean of this many latest results


@dataclass
class Attempt:
    session: str
    exam: str
    mode: str                                   # exam | practice
    score: float                                # on the 300-point scale
    passed: bool
    graded_at: float
    objectives: dict[str, float]                # objective id -> share of points (0..1)
    tasks: dict[str, float]                     # task id -> share of points; {} if never recorded
    by_difficulty: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] | None = None       # the session's results.json, when it still exists


@dataclass
class History:
    attempts: list[Attempt]                     # oldest first
    unreadable: int                             # history lines that could not be used


def _number(value: Any, default: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _shares(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    return {str(k): min(max(_number(v), 0.0), 1.0) for k, v in value.items()}


def session_results(session: str, sessions_dir: Path | None = None) -> dict[str, Any] | None:
    """A session's results.json, or None. The id is checked before it goes anywhere near a path."""
    if not SESSION_ID.match(session):
        return None
    try:
        data = json.loads(((sessions_dir or paths.SESSIONS) / session / "results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("tasks"), list) else None


def load(history_file: Path | None = None, sessions_dir: Path | None = None) -> History:
    try:
        lines = (history_file or paths.HISTORY_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return History([], 0)
    attempts: list[Attempt] = []
    unreadable = 0
    for line in lines:
        if not line.strip():
            continue
        try:
            h = json.loads(line)
            session, exam = str(h["session"]), str(h["exam"])
        except (ValueError, KeyError, TypeError):
            unreadable += 1
            continue
        if not SESSION_ID.match(session) or exam not in ("rhcsa", "rhce"):
            unreadable += 1
            continue
        results = session_results(session, sessions_dir)
        tasks = _shares(h.get("tasks"))
        if not tasks and results:      # a line from before the history recorded tasks
            tasks = {str(t.get("task_id")): (_number(t.get("points")) / _number(t.get("points_possible"))
                                             if _number(t.get("points_possible")) else 0.0)
                     for t in results["tasks"] if isinstance(t, dict)}
        attempts.append(Attempt(session, exam, "exam" if h.get("mode") == "exam" else "practice",
                                _number(h.get("score")), bool(h.get("passed")), _number(h.get("graded_at")),
                                _shares(h.get("objectives")), tasks,
                                h.get("by_difficulty") if isinstance(h.get("by_difficulty"), dict) else {}, results))
    attempts.sort(key=lambda a: a.graded_at)
    return History(attempts, unreadable)


def select(attempts: list[Attempt], exam: str, exams_only: bool = False) -> list[Attempt]:
    return [a for a in attempts if a.exam == exam and (a.mode == "exam" or not exams_only)]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _trend(values: list[float]) -> float | None:
    """The last two results against the three before them; None with fewer than three results."""
    if len(values) < 3:
        return None
    return _mean(values[-2:]) - _mean(values[-5:-2])


def overview(attempts: list[Attempt]) -> dict[str, Any]:
    scores = [a.score for a in attempts]
    used = sorted(_number(a.results.get("elapsed_s")) / 60 for a in attempts if a.results and a.mode == "exam")
    return {
        "attempts": len(attempts),
        "passes": sum(1 for a in attempts if a.passed),
        "best": max(scores, default=None),
        "last": scores[-3:],
        "median_minutes": used[len(used) // 2] if used else None,
    }


@dataclass
class Row:
    key: str
    title: str
    group: str                  # the domain
    tested: int
    share: float | None         # mean of the latest results, None if never tested
    trend: float | None
    last: float | None          # when it was last tested (epoch seconds)
    last_share: float | None = None
    checks: list[dict[str, Any]] = field(default_factory=list)


def objective_rows(attempts: list[Attempt], objectives: dict[str, tuple[str, str]]) -> list[Row]:
    """objectives: id -> (text, domain title), the official list in its order. One row each,
    also for objectives no attempt has tested yet."""
    seen: dict[str, list[tuple[float, float]]] = {}
    for a in attempts:
        for oid, share in a.objectives.items():
            seen.setdefault(oid, []).append((a.graded_at, share))
    rows = []
    for oid, (text, domain) in objectives.items():
        results = seen.get(oid, [])
        values = [share for _, share in results]
        rows.append(Row(oid, text, domain, len(values), _mean(values[-RECENT:]) if values else None,
                        _trend(values), results[-1][0] if results else None, values[-1] if values else None))
    return rows


def weakest(rows: list[Row], count: int = 5, at_least: int = 2) -> list[Row]:
    """The rows that keep costing points: tested at least twice, lowest first."""
    tested = [r for r in rows if r.tested >= at_least and r.share is not None and r.share < 1.0]
    return sorted(tested, key=lambda r: (r.share, -r.tested))[:count]


def task_rows(attempts: list[Attempt], titles: dict[str, tuple[str, str]]) -> list[Row]:
    """One row per task the candidate has met, weakest first. titles: task id -> (title, domain).
    Each row's checks say how often a check failed, and how often it passed before the reboot
    and failed after it, over the attempts whose results still exist."""
    seen: dict[str, list[tuple[float, float]]] = {}
    checks: dict[str, dict[str, dict[str, Any]]] = {}
    for a in attempts:
        for tid, share in a.tasks.items():
            seen.setdefault(tid, []).append((a.graded_at, share))
        for t in (a.results or {}).get("tasks", []):
            if not isinstance(t, dict):
                continue
            lost = set(t.get("not_persistent") or [])
            for c in t.get("post") or []:
                if not isinstance(c, dict) or c.get("status") == "n/a":
                    continue
                entry = checks.setdefault(str(t.get("task_id")), {}).setdefault(
                    f"{c.get('id')}@{c.get('node')}",
                    {"desc": str(c.get("desc", "")), "node": str(c.get("node", "")), "guard": bool(c.get("guard")),
                     "seen": 0, "failed": 0, "not_persistent": 0})
                entry["seen"] += 1
                entry["failed"] += c.get("status") != "pass"
                entry["not_persistent"] += c.get("id") in lost
    rows = []
    for tid, results in seen.items():
        values = [share for _, share in results]
        title, domain = titles.get(tid, (tid, ""))
        rows.append(Row(tid, title, domain, len(values), _mean(values[-RECENT:]), _trend(values), results[-1][0],
                        values[-1], sorted(checks.get(tid, {}).values(), key=lambda c: -c["failed"])))
    return sorted(rows, key=lambda r: (r.share, -r.tested, r.key))


def repeated_failures(rows: list[Row], count: int = 5) -> list[tuple[Row, dict[str, Any]]]:
    """The checks that failed most often, at least twice: (task row, check)."""
    found = [(r, c) for r in rows for c in r.checks if c["failed"] >= 2]
    return sorted(found, key=lambda rc: (-rc[1]["failed"], rc[0].key))[:count]


def not_persistent_total(attempts: list[Attempt]) -> int:
    """Answers that worked before the grading reboot and not after it, over all attempts."""
    return sum(len(t.get("not_persistent") or []) for a in attempts
               for t in (a.results or {}).get("tasks", []) if isinstance(t, dict))
