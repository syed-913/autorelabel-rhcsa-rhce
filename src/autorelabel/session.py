"""Exam/practice sessions: the state machine, the event journal and timekeeping.

Timekeeping: the proctor process adds elapsed time in small heartbeat steps
(capped), so time only counts while the proctor runs on this boot. A host
crash, reboot or suspend therefore pauses the clock automatically ("downtime is
forgiven"). With forgive_downtime off, elapsed time is plain wall-clock.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from . import paths
from .fsutil import append_line, atomic_write_json, read_json

# States
NEW = "new"
PROVISIONING = "provisioning"
PROVISION_FAILED = "provision_failed"
READY = "ready"
IN_PROGRESS = "in_progress"
INTERRUPTED = "interrupted"
LOCKED = "locked"
GRADING = "grading"
GRADING_INTERRUPTED = "grading_interrupted"
GRADED = "graded"
ABANDONED = "abandoned"

ACTIVE_STATES = {NEW, PROVISIONING, PROVISION_FAILED, READY, IN_PROGRESS, INTERRUPTED, LOCKED, GRADING,
                 GRADING_INTERRUPTED}
TRANSITIONS: dict[str, set[str]] = {
    NEW: {PROVISIONING, ABANDONED},
    PROVISIONING: {READY, PROVISION_FAILED, ABANDONED},
    PROVISION_FAILED: {PROVISIONING, ABANDONED},
    READY: {IN_PROGRESS, ABANDONED, PROVISIONING},
    IN_PROGRESS: {LOCKED, INTERRUPTED, ABANDONED},
    INTERRUPTED: {IN_PROGRESS, LOCKED, ABANDONED},
    LOCKED: {GRADING, ABANDONED},
    GRADING: {GRADED, GRADING_INTERRUPTED},
    GRADING_INTERRUPTED: {GRADING, ABANDONED},
    GRADED: {READY, ABANDONED},          # READY again after "Retake" (snapshot revert)
    ABANDONED: set(),
}

HEARTBEAT_INTERVAL = 5.0
HEARTBEAT_CAP = 20.0        # a longer gap (suspend, crash, stopped proctor) is not counted
SCHEMA = 1


class SessionError(RuntimeError):
    pass


def boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


@dataclass
class Session:
    id: str
    exam: str
    mode: str                        # exam | practice
    seed: int
    created: float
    state: str = NEW
    profile: str = "lite"
    provider: str = "libvirt"
    scoring: str = "partial"
    duration_s: int = 0
    tasks: list[dict[str, Any]] = field(default_factory=list)
    passwords: dict[str, str] = field(default_factory=dict)       # actual root passwords per node
    given: dict[str, str] = field(default_factory=dict)           # what the candidate is told
    accounts: dict[str, str] = field(default_factory=dict)        # RHCE: student / ansible passwords
    marks: dict[str, str] = field(default_factory=dict)           # task number -> done | flag
    started: float | None = None
    ended: float | None = None
    forgive_downtime: bool = True
    show_difficulty: bool = False
    warnings_minutes: list[int] = field(default_factory=lambda: [30, 10, 5, 1])
    bank_digest: str = ""
    box: dict[str, Any] = field(default_factory=dict)
    incidents: list[dict[str, Any]] = field(default_factory=list)
    broken_nodes: list[str] = field(default_factory=list)         # nodes a task leaves unbootable
    schema: int = SCHEMA

    # --- files --------------------------------------------------------------------------
    @property
    def dir(self) -> Path:
        return paths.SESSIONS / self.id

    @property
    def file(self) -> Path:
        return self.dir / "session.json"

    @property
    def heartbeat_file(self) -> Path:
        return self.dir / "heartbeat.json"

    @property
    def journal(self) -> Path:
        return self.dir / "events.jsonl"

    @property
    def results_file(self) -> Path:
        return self.dir / "results.json"

    @property
    def report_file(self) -> Path:
        return self.dir / "report.md"

    @property
    def lock_file(self) -> Path:
        return self.dir / "proctor.lock"

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.file, asdict(self), mode=0o600)

    def event(self, event_name: str, /, **data: Any) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        append_line(self.journal, json.dumps({"ts": time.time(), **data, "event": event_name}, sort_keys=True))

    def transition(self, new: str, **data: Any) -> None:
        if new != self.state and new not in TRANSITIONS.get(self.state, set()):
            raise SessionError(f"invalid transition {self.state} -> {new}")
        old, self.state = self.state, new
        self.event("state", old=old, new=new, **data)
        self.save()

    def incident(self, node: str, kind: str, message: str) -> None:
        self.incidents.append({"ts": time.time(), "node": node, "kind": kind, "message": message})
        self.event("incident", node=node, kind=kind, message=message)
        self.save()

    # --- time -----------------------------------------------------------------------------
    def heartbeat(self) -> dict[str, Any]:
        return read_json(self.heartbeat_file, default={}) or {}

    def elapsed(self, now: float | None = None) -> float:
        now = now or time.time()
        if self.started is None:
            return 0.0
        if not self.forgive_downtime:
            return min((self.ended or now) - self.started, float(self.duration_s))
        hb = self.heartbeat()
        elapsed = float(hb.get("elapsed", 0.0))
        if self.state == IN_PROGRESS and hb.get("boot_id") == boot_id():
            elapsed += max(0.0, min(now - float(hb.get("wall", now)), HEARTBEAT_CAP))
        return min(elapsed, float(self.duration_s))

    def remaining(self, now: float | None = None) -> float:
        return max(0.0, self.duration_s - self.elapsed(now))

    def tick(self, now: float | None = None) -> dict[str, Any]:
        """Called by the proctor every HEARTBEAT_INTERVAL. Adds at most HEARTBEAT_CAP
        seconds, so gaps (suspend, crash, stopped proctor) are not charged."""
        now = now or time.time()
        hb = self.heartbeat()
        bid = boot_id()
        elapsed = float(hb.get("elapsed", 0.0))
        last = float(hb.get("wall", now))
        if hb.get("boot_id") == bid:
            gap = now - last
            if gap > HEARTBEAT_CAP:
                self.event("downtime_forgiven", seconds=round(gap))
            else:
                elapsed += max(0.0, gap)
        elif hb:
            self.event("host_reboot_detected", previous_boot=hb.get("boot_id"))
        hb = {**hb, "elapsed": min(elapsed, float(self.duration_s)), "wall": now, "boot_id": bid}
        atomic_write_json(self.heartbeat_file, hb)
        return hb

    def fired_warnings(self) -> set[int]:
        return set(self.heartbeat().get("warnings", []))

    def mark_warning(self, minutes: int) -> None:
        hb = self.heartbeat()
        hb["warnings"] = sorted(set(hb.get("warnings", [])) | {minutes})
        atomic_write_json(self.heartbeat_file, hb)


# --- persistence ------------------------------------------------------------------------------

CURRENT = paths.SESSIONS / "current"


def new_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def load(session_id: str) -> Session:
    raw = read_json(paths.SESSIONS / session_id / "session.json")
    if raw is None:
        raise SessionError(f"no such session: {session_id}")
    known = {f for f in Session.__dataclass_fields__}
    return Session(**{k: v for k, v in raw.items() if k in known})


def current() -> Session | None:
    try:
        sid = CURRENT.read_text().strip()
    except OSError:
        return None
    try:
        s = load(sid)
    except (SessionError, json.JSONDecodeError, TypeError):
        return None
    return s if s.state in ACTIVE_STATES or s.state == GRADED else None


def set_current(s: Session | None) -> None:
    paths.SESSIONS.mkdir(parents=True, exist_ok=True)
    if s is None:
        CURRENT.unlink(missing_ok=True)
    else:
        CURRENT.write_text(s.id + "\n")


def all_sessions() -> list[Session]:
    out = []
    for d in sorted(paths.SESSIONS.glob("*/session.json"), reverse=True):
        try:
            out.append(load(d.parent.name))
        except (SessionError, json.JSONDecodeError, TypeError):
            continue
    return out


def rebuild_from_journal(session_id: str) -> str | None:
    """Recover the last known state from events.jsonl if session.json is damaged."""
    last = None
    try:
        for line in (paths.SESSIONS / session_id / "events.jsonl").read_text().splitlines():
            ev = json.loads(line)
            if ev.get("event") == "state":
                last = ev.get("new")
    except (OSError, json.JSONDecodeError):
        return None
    return last
