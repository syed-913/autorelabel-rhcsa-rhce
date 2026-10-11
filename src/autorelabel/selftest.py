"""Task self-test on real VMs: the quality gate every task must pass.

For each task:
  1. pre-state:   right after setup, the task must NOT score full marks
  2. reference:   solution scripts, then a reboot → full marks
  3. alternative: each tests/alt-*.sh, then a reboot → full marks (valid methods aren't punished)
  4. mistakes:    each tests/mistake-*.sh, then a reboot → NOT full marks (classic errors are caught)

Compatible tasks run together in batches (one reboot per round) to keep this fast.
Results are stored per task with a digest of the task's files, so edited tasks
are re-tested and the coverage report can mark verified tasks.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import box, console, labfacts, paths, remote
from . import session as S
from .bank import Bank, render
from .bank.model import Task
from .bank.select import _disk_capacity_mib
from .engine import EXAM_START, Engine, EngineError
from .fsutil import atomic_write_json, read_json

LineFn = Callable[[str], None]
# Anchors are solved in this order (RHCE: configuration → SSH access → repositories through Ansible).
ANCHOR_ORDER = ("network-node1", "ansible-setup", "managed-access", "repos", "root-reset")


def task_digest(task: Task) -> str:
    h = hashlib.sha256()
    for p in sorted(task.path.rglob("*")):
        if p.is_file():
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:12]


def results_file(exam: str) -> Path:
    return paths.BANKS / exam / "selftest.json"


def load_results(exam: str) -> dict[str, Any]:
    return read_json(results_file(exam), default={}) or {}


def verified(bank: Bank) -> dict[str, str]:
    """task id -> stamp, for tasks whose current files passed self-test."""
    res = load_results(bank.exam)
    out = {}
    for tid, task in bank.tasks.items():
        r = res.get(tid)
        if r and r.get("status") == "pass" and r.get("digest") == task_digest(task):
            out[tid] = f"{r.get('box', '?')} {r.get('date', '')}"
    return out


def plan_batches(bank: Bank, tasks: list[Task], max_size: int = 8) -> list[list[Task]]:
    """Group tasks that can share a lab: no shared exclusive groups, disk budgets fit.
    Tasks that break boot run alone, and so do anchors: their alternative and mistake tests
    deliberately break what everything else depends on (network, repositories, root access)."""
    cap = _disk_capacity_mib(bank.exam)
    batches: list[list[Task]] = []
    for t in sorted(tasks, key=lambda x: (x.breaks_boot or bool(x.anchor), x.id)):
        placed = False
        if not (t.breaks_boot or t.anchor):
            for b in batches:
                if len(b) >= max_size or any(x.breaks_boot or x.anchor for x in b):
                    continue
                if set(t.exclusive) & {e for x in b for e in x.exclusive}:
                    continue
                disk: dict[str, int] = {}
                for x in [*b, t]:
                    for d, mib in (x.resources.get("disk") or {}).items():
                        disk[d] = disk.get(d, 0) + int(mib)
                if any(v > cap.get(d, 0) for d, v in disk.items()):
                    continue
                b.append(t)
                placed = True
                break
        if not placed:
            batches.append([t])
    return batches


class SelfTest:
    def __init__(self, engine: Engine, exam: str, on_line: LineFn | None = None):
        self.engine = engine
        self.exam = exam
        self.bank = engine.bank(exam)
        self.lab = engine.lab(exam)
        self.say = on_line or (lambda s: None)
        self.lib = (paths.BANKS / "lib" / "setup-lib.sh").read_text()

    # --- helpers --------------------------------------------------------------------------------
    def _run_on(self, sess: S.Session, entry: dict[str, Any], script: Path, node: str) -> tuple[bool, str]:
        facts = self.lab.facts()
        env = {**render.env_for(entry["params"], facts), "AR_NODE": node, "AR_TASK": entry["task"],
               "AR_ROOT_PASSWORD": sess.passwords.get(node, ""),
               **{f"AR_{u.upper()}_PASSWORD": pw for u, pw in sess.accounts.items()}}
        task = self.bank.tasks[entry["task"]]
        if task.breaks_boot and node == task.node:
            # The node is in emergency mode: type the script on its serial console, as a candidate would.
            lines = [f"export {k}={json.dumps(str(v))}" for k, v in env.items() if k.startswith(("P_", "LAB_"))]
            body = [ln for ln in script.read_text().splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
            log_file = sess.dir / f"console-{entry['task']}-{node}-{script.stem}.log"
            stamp = f"\n===== {time.strftime('%H:%M:%S')} =====\n"
            try:
                out = console.run_commands(self.lab.vm(node).domain, sess.passwords.get(node, ""),
                                           "\n".join(lines + body), hv=self.lab.hv, reboot=True)
                with open(log_file, "a", encoding="utf-8") as fh:   # one section per attempt
                    fh.write(stamp + out)
                # let it come back (a mistake test may leave it unbootable: then the grader finds out)
                remote.wait_reachable(self.lab.target(node), timeout=180)
                return True, out[-400:]
            except console.ConsoleError as exc:
                with open(log_file, "a", encoding="utf-8") as fh:
                    fh.write(stamp + str(exc))
                return False, str(exc)
        res = remote.run_script(self.lab.target(node), self.lib + "\n" + script.read_text(), env=env, timeout=900)
        return res.ok, (res.out + res.err)[-800:]

    def _scripts_for(self, task: Task, kind: str, index: int = 0) -> dict[str, Path]:
        """kind: solution | alt | mistake. Returns {node: script}."""
        if kind == "solution":
            return task.solution_scripts
        groups = task.test_groups(kind)
        return groups[index][1] if index < len(groups) else {}

    def _apply(self, sess: S.Session, entries: list[dict[str, Any]], kind: str, index: int
               ) -> tuple[list[str], dict[str, str]]:
        """Apply this round's script (reference solution, or alternative/mistake test number
        `index`) for each task. A task without one gets its reference solution instead, like a
        real exam where everything else is solved: left in its starting state it could break the
        others (a node's lab connection still down). Returns the tasks whose own script ran and
        {task id: error} for scripts that failed. A failing script only fails its own task; a
        failing anchor fails the round (everything else depends on it)."""
        failed: dict[str, str] = {}
        participants: list[str] = []
        by_anchor = {self.bank.tasks[e["task"]].anchor: e for e in entries if self.bank.tasks[e["task"]].anchor}
        ordered = [by_anchor[a] for a in ANCHOR_ORDER if a in by_anchor]
        ordered += [e for e in entries if not self.bank.tasks[e["task"]].anchor]
        for e in ordered:
            task = self.bank.tasks[e["task"]]
            scripts = self._scripts_for(task, kind, index)
            if scripts:
                participants.append(task.id)
            else:
                scripts = task.solution_scripts
            facts = self.lab.facts()
            for node, script in [(n, sc) for target, sc in scripts.items()
                                 for n in labfacts.script_nodes(target, facts)]:
                ok, out = self._run_on(sess, e, script, node)
                if not ok:
                    msg = f"{script.name} failed on {node}: {out.strip()[-300:]}"
                    if task.anchor:
                        raise EngineError("self-test script failed", f"{task.id} (anchor): {msg}")
                    failed.setdefault(task.id, msg)
        return participants, failed

    def _grade(self, sess: S.Session, reboot: bool) -> dict[str, dict[str, Any]]:
        results = self.engine.grade(sess, official=False, reboot=reboot)
        return {t["task_id"]: t for t in results["tasks"]}

    @staticmethod
    def _full(t: dict[str, Any]) -> bool:
        return bool(t["post"]) and all(c["status"] == "pass" for c in t["post"])

    @staticmethod
    def _failures(t: dict[str, Any]) -> str:
        return "; ".join(f"{c['id']}={c['status']} {c['detail'][:120]}" for c in t["post"] if c["status"] != "pass")

    @staticmethod
    def _infra_trouble(graded: dict[str, dict[str, Any]]) -> bool:
        return any(c["status"] == "unreachable" for t in graded.values() for c in t["post"])

    def _retry_round(self, sess: S.Session, kind: str, index: int
                     ) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        """A round that should score full marks lost a node (host hiccup, paused VM):
        run it once more from the exam starting point before blaming the task."""
        self.say(f"    a node was unreachable during the {kind} round; retrying it once")
        self._restart_from_exam_start(sess)
        _who, failed = self._apply(sess, sess.tasks, kind, index)
        return self._grade(sess, reboot=True), failed

    def _restart_from_exam_start(self, sess: S.Session) -> None:
        self.lab.revert(EXAM_START)
        self.lab.start_all()
        healthy = [n for n in self.lab.names() if n not in sess.broken_nodes]
        missing = self.lab.wait_all(healthy, timeout=600)
        if missing:
            raise EngineError(f"{', '.join(missing)} did not start after revert")

    # --- main ---------------------------------------------------------------------------------------
    def run(self, task_ids: list[str] | None = None, *, only_changed: bool = False) -> dict[str, Any]:
        tasks = [self.bank.tasks[t] for t in (task_ids or sorted(self.bank.tasks))]
        if only_changed:
            ok = verified(self.bank)
            tasks = [t for t in tasks if t.id not in ok]
        results = load_results(self.exam)
        manifest = box.manifest(self.engine.settings, self.engine.settings.provider) or {}
        stamp = {"box": f"RHEL {manifest.get('rhel_version', '?')} {manifest.get('version', '')}".strip(),
                 "date": time.strftime("%Y-%m-%d")}
        batches = plan_batches(self.bank, tasks)
        self.say(f"self-testing {len(tasks)} task(s) in {len(batches)} batch(es)")
        for n, batch in enumerate(batches, 1):
            self.say(f"--- batch {n}/{len(batches)}: {', '.join(t.id.split('.', 1)[1] for t in batch)}")
            outcome = self._run_batch(batch)
            for tid, (status, detail) in outcome.items():
                results[tid] = {"status": status, "detail": detail, "digest": task_digest(self.bank.tasks[tid]),
                                **stamp}
                self.say(f"    {status.upper():4} {tid} {detail}")
            atomic_write_json(results_file(self.exam), results)
        return results

    def _run_batch(self, batch: list[Task]) -> dict[str, tuple[str, str]]:
        outcome: dict[str, tuple[str, str]] = {t.id: ("pass", "") for t in batch}

        def fail(tid: str, why: str) -> None:
            if outcome[tid][0] == "pass":
                outcome[tid] = ("fail", why)

        try:
            sess = self.engine.create(self.exam, mode="practice", task_ids=[t.id for t in batch], timed=False)
            sess.mode = "selftest"
            sess.save()
            self.engine.prepare(sess, on_step=lambda s: self.say(f"    {s}"))
            # 1. pre-state
            pre = self._grade(sess, reboot=False)
            for t in batch:
                if t.id in pre and self._full(pre[t.id]):
                    fail(t.id, "pre-state already scores full marks (setup or checks too weak)")
            # 2. reference
            _who, failed = self._apply(sess, sess.tasks, "solution", 0)
            ref = self._grade(sess, reboot=True)
            if self._infra_trouble(ref):
                ref, failed = self._retry_round(sess, "solution", 0)
            for tid, msg in failed.items():
                fail(tid, f"reference solution script failed: {msg}")
            for t in batch:
                if t.id in failed:
                    continue
                if not self._full(ref.get(t.id, {"post": []})):
                    fail(t.id, "reference solution not full marks: " + self._failures(ref.get(t.id, {"post": []})))
            # 3/4. alternatives and mistakes, round by round
            for kind, want_full in (("alt", True), ("mistake", False)):
                rounds = max((len(t.test_groups(kind)) for t in batch), default=0)
                for i in range(rounds):
                    self._restart_from_exam_start(sess)
                    who, failed = self._apply(sess, sess.tasks, kind, i)
                    got = self._grade(sess, reboot=True)
                    if want_full and self._infra_trouble(got):
                        got, failed = self._retry_round(sess, kind, i)
                    for t in batch:
                        if t.id not in who or len(t.test_groups(kind)) <= i:
                            continue
                        name = t.test_groups(kind)[i][0]
                        if t.id in failed:
                            fail(t.id, f"{kind} test {name}: script failed: {failed[t.id]}")
                            continue
                        full = self._full(got.get(t.id, {"post": []}))
                        if want_full and not full:
                            fail(t.id, f"valid alternative {name} was not accepted: "
                                       + self._failures(got.get(t.id, {"post": []})))
                        if not want_full and full:
                            fail(t.id, f"common mistake {name} was not caught")
            self.engine.abandon(sess)
        except EngineError as exc:
            for t in batch:
                fail(t.id, f"{exc} {exc.hint}".strip()[:600])
        except Exception as exc:  # report, keep going with the next batch
            for t in batch:
                fail(t.id, f"self-test crashed: {exc!r}"[:600])
        return outcome


def summary(exam: str) -> str:
    res = load_results(exam)
    passed = sum(1 for r in res.values() if r.get("status") == "pass")
    return json.dumps({"tested": len(res), "passed": passed})
