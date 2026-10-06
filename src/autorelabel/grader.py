"""Grading: pre-reboot pass → verified reboot → post-reboot pass → scored report.

Only the post-reboot pass counts. The pre-reboot pass exists to flag work that
"worked before the reboot but not after" (not persistent). Progress is
checkpointed after every check so grading resumes exactly where it stopped.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any

from . import console, log, paths, remote
from .bank import Bank, render
from .fsutil import append_line, atomic_write_json, read_json
from .lab import Lab
from .providers import libvirt as lv
from .session import Session

_log = log.get("grader")

SHUTDOWN_GRACE = 90          # seconds for a normal reboot before ACPI
ACPI_GRACE = 60              # seconds after ACPI before a hard reset
BOOT_TIMEOUT = 300           # base wait for a node to come back
RELABEL_EXTENSION = 900      # extra time while SELinux relabels
MAX_BOOT_CYCLES = 3


@dataclass
class CheckResult:
    id: str
    desc: str
    node: str
    status: str              # pass | fail | error | unreachable
    weight: float
    covers: list[str]
    detail: str = ""


@dataclass
class TaskResult:
    number: int
    task_id: str
    title: str
    difficulty: str
    domain: str
    objectives: list[str]
    points_possible: int
    points: float = 0.0
    pre: list[CheckResult] = field(default_factory=list)
    post: list[CheckResult] = field(default_factory=list)
    not_persistent: list[str] = field(default_factory=list)


EventFn = Callable[[str, dict[str, Any]], None]


class Grader:
    def __init__(self, session: Session, lab: Lab, bank: Bank, on_event: EventFn | None = None):
        self.s = session
        self.lab = lab
        self.bank = bank
        self.emit = on_event or (lambda kind, data: None)
        self.facts = lab.facts()
        self.checkpoint_file = session.dir / "grading.json"

    # --- checkpoints ------------------------------------------------------------------------
    def _load_cp(self) -> dict[str, Any]:
        return read_json(self.checkpoint_file, default={}) or {}

    def _save_cp(self, cp: dict[str, Any]) -> None:
        atomic_write_json(self.checkpoint_file, cp)

    # --- running checks --------------------------------------------------------------------
    def _exam_nodes(self) -> list[str]:
        return [v.name for v in self.lab.vms if v.spec.role != "utility"]

    def _check_jobs(self) -> list[tuple[int, Any, dict[str, Any], str]]:
        jobs = []
        for entry in self.s.tasks:
            task = self.bank.tasks.get(entry["task"])
            if task is None:
                continue
            for chk in task.checks:
                jobs.append((entry["number"], chk, entry["params"], chk.on or task.node))
        return jobs

    def run_pass(self, phase: str, cp: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Run every check once. Returns {"<task#>:<check-id>": result-dict}."""
        done: dict[str, dict[str, Any]] = cp.setdefault(phase, {})
        jobs = [j for j in self._check_jobs() if f"{j[0]}:{j[1].id}" not in done]
        by_node: dict[str, list] = {}
        for j in jobs:
            by_node.setdefault(j[3], []).append(j)
        unreachable: dict[str, str] = {}
        for node in by_node:
            if not remote.reachable(self.lab.target(node), timeout=20):
                unreachable[node] = self._diagnose(node).message
        total = len(self._check_jobs())

        def run_node(node: str) -> None:
            t = self.lab.target(node)
            for number, chk, params, _ in by_node[node]:
                key = f"{number}:{chk.id}"
                if node in unreachable:
                    res = CheckResult(chk.id, chk.desc, node, "unreachable", chk.weight, list(chk.covers),
                                      unreachable[node])
                else:
                    res = self._run_check(t, node, chk, params)
                done[key] = asdict(res)
                self._save_cp(cp)
                self.emit("check", {"phase": phase, "done": len(done), "total": total, "task": number,
                                    "check": chk.id, "status": res.status})

        with ThreadPoolExecutor(max_workers=max(1, len(by_node))) as pool:
            list(pool.map(run_node, list(by_node)))
        return done

    def _run_check(self, t: remote.Target, node: str, chk: Any, params: dict[str, Any]) -> CheckResult:
        ctx = {**params, "lab": self.facts}
        try:
            script = render.render(chk.run, ctx)
            desc = render.render(chk.desc, ctx)
        except render.RenderError as exc:
            return CheckResult(chk.id, chk.desc, node, "error", chk.weight, list(chk.covers),
                               f"template error: {exc}")
        env = render.env_for(params, self.facts)
        res = remote.run_script(t, script + "\n", env=env, timeout=chk.timeout)
        if res.timed_out:
            status, detail = "error", f"check timed out after {chk.timeout}s"
        elif res.rc == 255 and not res.out:
            status, detail = "unreachable", res.err.strip()[-200:]
        elif res.rc == 0:
            status, detail = "pass", ""
        else:
            status, detail = "fail", (res.out.strip() or res.err.strip())[-300:]
        return CheckResult(chk.id, desc, node, status, chk.weight, list(chk.covers), detail)

    # --- reboot ---------------------------------------------------------------------------
    def _diagnose(self, node: str) -> console.Diagnosis:
        dom = self.lab.vm(node).domain
        st, reason = lv.state(dom)
        if st != "running":
            return console.Diagnosis("off", f"VM is {st}{f' ({reason})' if reason else ''}.")
        text = console.probe(dom)
        return console.diagnose(text)

    def verified_reboot(self, nodes: list[str]) -> dict[str, str]:
        """Reboot each node from inside, escalating to ACPI and hard reset if it hangs.
        Returns {node: problem} for nodes that did not come back."""
        problems: dict[str, str] = {}

        def one(node: str) -> None:
            t = self.lab.target(node)
            dom = self.lab.vm(node).domain
            st, _ = lv.state(dom)
            if st == "paused":
                lv.resume(dom)
            elif st in ("shut off", "crashed"):
                self.s.incident(node, "powered-off", "was powered off at grading time; powered on")
                lv.start(dom)
            before = remote.boot_id(t)
            self.emit("reboot", {"node": node, "stage": "rebooting"})
            if before:
                remote.run_cmd(t, "systemctl reboot", timeout=15)
            else:
                lv.reset(dom)
                self.s.incident(node, "unreachable-before-reboot",
                                "was not reachable before the grading reboot; it was reset")
            remote.close_master(t)
            if before:
                # wait for the node to actually go down (or come back with a new boot id)
                start = time.monotonic()
                escalated = None
                while True:
                    bid = remote.boot_id(t)
                    if bid is None or bid != before:
                        break
                    elapsed = time.monotonic() - start
                    if elapsed > SHUTDOWN_GRACE and escalated is None:
                        lv.reboot_acpi(dom)
                        escalated = "acpi"
                    elif elapsed > SHUTDOWN_GRACE + ACPI_GRACE and escalated == "acpi":
                        lv.reset(dom)
                        escalated = "reset"
                        self.s.incident(node, "forced-reset",
                                        "did not shut down within 2.5 minutes and was hard-reset; "
                                        "check for hung mounts (e.g. NFS without _netdev) or services")
                        break
                    time.sleep(3)
            # wait for it to come back
            deadline = time.monotonic() + BOOT_TIMEOUT
            next_probe = time.monotonic() + 90
            extended = False
            last_diag = None
            while True:
                bid = remote.boot_id(t)
                if bid and bid != before:
                    self.emit("reboot", {"node": node, "stage": "back"})
                    return
                if time.monotonic() > next_probe:
                    next_probe = time.monotonic() + 30
                    prev = last_diag
                    last_diag = self._diagnose(node)
                    if last_diag.kind == "login" and prev is not None and prev.kind == "login":
                        # Booted to a login prompt twice in a row, yet SSH still fails: locked out.
                        last_diag = console.Diagnosis(
                            "lockout", "booted normally, but the grader cannot log in (sshd, PAM, the vagrant "
                                       "account, mgmt0, or SELinux labels such as /etc/shadow)")
                        break
                    if last_diag.kind == "relabel" and not extended:
                        deadline += RELABEL_EXTENSION
                        extended = True
                        self.emit("reboot", {"node": node, "stage": "relabelling"})
                    elif last_diag.terminal:
                        break
                if time.monotonic() > deadline:
                    break
                time.sleep(5)
            diag = last_diag or self._diagnose(node)
            problems[node] = f"{node} did not come back after the reboot: {diag.message}"
            self.s.incident(node, f"boot-{diag.kind}", diag.message)
            self.emit("reboot", {"node": node, "stage": "failed", "message": diag.message})

        with ThreadPoolExecutor(max_workers=max(1, len(nodes))) as pool:
            list(pool.map(one, nodes))
        return problems

    # --- scoring ----------------------------------------------------------------------------
    def score(self, cp: dict[str, Any]) -> dict[str, Any]:
        strict = self.s.scoring == "strict"
        results: list[TaskResult] = []
        for entry in self.s.tasks:
            task = self.bank.tasks.get(entry["task"])
            if task is None:
                continue
            tr = TaskResult(entry["number"], task.id, render.render(task.title, {**entry["params"],
                                                                              "lab": self.facts}),
                            task.difficulty, task.domain, list(task.objectives), entry["points"])
            for chk in task.checks:
                key = f"{entry['number']}:{chk.id}"
                pre = cp.get("pre", {}).get(key)
                post = cp.get("post", {}).get(key)
                if pre:
                    tr.pre.append(CheckResult(**pre))
                if post:
                    tr.post.append(CheckResult(**post))
                if pre and post and pre["status"] == "pass" and post["status"] != "pass":
                    tr.not_persistent.append(chk.id)
            total_w = sum(c.weight for c in tr.post) or 1.0
            ok_w = sum(c.weight for c in tr.post if c.status == "pass")
            if strict:
                tr.points = float(tr.points_possible) if ok_w == total_w and tr.post else 0.0
            else:
                tr.points = round(tr.points_possible * ok_w / total_w, 2)
            results.append(tr)
        bp = self.bank.blueprint
        score = round(sum(t.points for t in results), 1)
        by_diff: dict[str, list[float]] = {}
        by_domain: dict[str, list[float]] = {}
        for t in results:
            by_diff.setdefault(t.difficulty, [0.0, 0.0])
            by_diff[t.difficulty][0] += t.points
            by_diff[t.difficulty][1] += t.points_possible
            by_domain.setdefault(t.domain, [0.0, 0.0])
            by_domain[t.domain][0] += t.points
            by_domain[t.domain][1] += t.points_possible
        possible = sum(t.points_possible for t in results)
        # Practice sets are scaled to the 300-point scale for the pass/fail comparison.
        scaled = score if possible == bp.total_points or not possible else round(score * bp.total_points / possible, 1)
        return {
            "session": self.s.id,
            "exam": self.s.exam,
            "mode": self.s.mode,
            "scoring": self.s.scoring,
            "score": score,
            "possible": possible,
            "scaled_score": scaled,
            "total_points": bp.total_points,
            "pass_mark": bp.pass_mark,
            "passed": scaled >= bp.pass_mark,
            "by_difficulty": {k: {"points": round(v[0], 1), "possible": v[1]} for k, v in by_diff.items()},
            "by_domain": {k: {"points": round(v[0], 1), "possible": v[1]} for k, v in by_domain.items()},
            "tasks": [asdict(t) for t in results],
            "incidents": self.s.incidents,
            "elapsed_s": round(self.s.elapsed()),
            "duration_s": self.s.duration_s,
            "graded_at": time.time(),
        }

    # --- the whole thing -------------------------------------------------------------------------
    def grade(self, *, reboot: bool = True) -> dict[str, Any]:
        cp = self._load_cp()
        self.lab.start_all()
        self.lab.resume_all()
        nodes = self._exam_nodes()
        if not cp.get("pre_done"):
            self.emit("phase", {"phase": "pre", "label": "Checking your work (before reboot)"})
            self.run_pass("pre", cp)
            cp["pre_done"] = True
            self._save_cp(cp)
        if reboot and not cp.get("reboot_done"):
            self.emit("phase", {"phase": "reboot", "label": "Rebooting every exam node"})
            cp["reboot_problems"] = self.verified_reboot(nodes)
            cp["reboot_done"] = True
            self._save_cp(cp)
        if not cp.get("post_done"):
            self.emit("phase", {"phase": "post", "label": "Grading (after reboot)"})
            if not reboot:
                cp["post"] = dict(cp.get("pre", {}))
            else:
                self.run_pass("post", cp)
            cp["post_done"] = True
            self._save_cp(cp)
        results = self.score(cp)
        return results


def write_report(session: Session, bank: Bank, results: dict[str, Any]) -> str:
    """Markdown report saved next to the results (also shown by the TUI)."""
    r = results
    lines = [
        f"# {r['exam'].upper()} {'exam' if r['mode'] == 'exam' else 'practice'} results",
        "",
        f"**Score: {r['scaled_score']:.0f} / {r['total_points']}** — "
        f"{'PASS ✅' if r['passed'] else 'FAIL ❌'} (pass mark {r['pass_mark']})",
        "",
        f"Session `{r['session']}` · scoring: {r['scoring']} · time used: "
        f"{r['elapsed_s'] // 60} of {r['duration_s'] // 60} min",
        "",
        "| Difficulty | Points |",
        "|---|---|",
    ]
    for d in ("easy", "medium", "hard"):
        if d in r["by_difficulty"]:
            v = r["by_difficulty"][d]
            lines.append(f"| {d} | {v['points']:g} / {v['possible']} |")
    lines += ["", "| Domain | Points |", "|---|---|"]
    titles = {d.id: d.title for d in bank.objectives.domains}
    for dom, v in r["by_domain"].items():
        lines.append(f"| {titles.get(dom, dom)} | {v['points']:g} / {v['possible']} |")
    if r["incidents"]:
        lines += ["", "## Incidents", ""]
        for inc in r["incidents"]:
            lines.append(f"- **{inc['node']}**: {inc['message']}")
    lines += ["", "## Tasks", ""]
    for t in r["tasks"]:
        mark = "✅" if t["points"] == t["points_possible"] else ("⚠️" if t["points"] else "❌")
        lines.append(f"### {mark} Task {t['number']}: {t['title']} — {t['points']:g}/{t['points_possible']} "
                     f"({t['difficulty']})")
        for c in t["post"]:
            sym = {"pass": "✔", "fail": "✘", "error": "!", "unreachable": "⨯"}[c["status"]]
            extra = " — **worked before the reboot but not after (not persistent)**" \
                if c["id"] in t["not_persistent"] else ""
            detail = f" ({c['detail']})" if c["status"] != "pass" and c["detail"] else ""
            lines.append(f"- {sym} {c['desc']}{extra}{detail}")
        lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    session.report_file.write_text(text, encoding="utf-8")
    atomic_write_json(session.results_file, results)
    append_line(paths.HISTORY_FILE, json.dumps({
        "session": r["session"], "exam": r["exam"], "mode": r["mode"], "score": r["scaled_score"],
        "passed": r["passed"], "graded_at": r["graded_at"],
        "objectives": {o: (t["points"] / t["points_possible"] if t["points_possible"] else 0)
                       for t in r["tasks"] for o in t["objectives"]},
        "by_difficulty": r["by_difficulty"],
    }, sort_keys=True))
    return text


def objective_recency(exam: str) -> dict[str, float]:
    """Weights for the selector: objectives not seen in recent attempts get more weight."""
    seen: dict[str, int] = {}
    try:
        lines = paths.HISTORY_FILE.read_text().splitlines()
    except OSError:
        return {}
    recent = [json.loads(line) for line in lines[-10:] if line.strip()]
    for age, h in enumerate(reversed(recent)):
        if h.get("exam") != exam:
            continue
        for o in h.get("objectives", {}):
            seen.setdefault(o, age)
    from .bank import cached_bank

    out = {}
    for o in cached_bank(exam).objectives.objectives:
        out[o] = 2.0 if o not in seen else min(2.0, seen[o] * 0.4)
    return out

