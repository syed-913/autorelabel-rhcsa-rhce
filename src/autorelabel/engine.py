"""The exam engine: one UI-agnostic service used by the TUI and the CLI (and,
later, the browser UI). Every operation is safe to call again after a crash."""

from __future__ import annotations

import hashlib
import os
import random
import shutil
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import box, config, labfacts, ledger, log, paths, proc, remote, secrets_util
from . import session as S
from .bank import Bank, load_bank, render
from .bank.select import SelectedTask, generate, practice
from .config import Settings
from .grader import Grader, objective_recency, write_report
from .lab import Lab, LabError

_log = log.get("engine")
StepFn = Callable[[str], None]
LineFn = Callable[[str], None]

BASELINE = "baseline"
EXAM_START = "exam-start"
SETUP_REPO = "/etc/yum.repos.d/zz-autorelabel-setup.repo"
CODE_SERVER_LOCAL_PORT = 18080        # first port tried for the code-server tunnel on this host


class EngineError(RuntimeError):
    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint


def fresh_checkpoint(directory: Path) -> Path:
    """A new checkpoint file for an unofficial grading. Numbered, not timestamped: self-test
    rounds can start within the same second, and reusing a finished checkpoint would return the
    previous round's results."""
    n = 1
    while (directory / f"check-{n:03d}.json").exists():
        n += 1
    return directory / f"check-{n:03d}.json"


def bank_digest(exam: str) -> str:
    h = hashlib.sha256()
    for p in sorted((paths.BANKS / exam).rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(paths.BANKS)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:12]


class Engine:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or config.load()

    # --- helpers ----------------------------------------------------------------------------
    def bank(self, exam: str) -> Bank:
        return load_bank(exam)

    def lab(self, exam: str) -> Lab:
        return Lab(self.settings, exam)

    def _setup_lib(self) -> str:
        return (paths.BANKS / "lib" / "setup-lib.sh").read_text()

    # --- session creation -------------------------------------------------------------------
    def create(self, exam: str, *, mode: str = "exam", seed: int | None = None,
               task_ids: list[str] | None = None, timed: bool = True, sweep: int | None = None) -> S.Session:
        if not self.settings.configured:
            raise EngineError("setup is not complete", "Run ./autorelabel to finish the setup wizard.")
        bank = self.bank(exam)
        seed = seed if seed is not None else random.SystemRandom().randrange(1, 10**9)
        if mode == "exam":
            selected = generate(bank, seed, objective_recency(exam))
        else:
            if not task_ids:
                raise EngineError("no tasks chosen for practice")
            selected = practice(bank, task_ids, seed, sweep=sweep)
        sess = S.Session(id=S.new_id(), exam=exam, mode=mode, seed=seed, created=time.time(),
                         profile=self.settings.profile, provider=self.settings.provider,
                         scoring=self.settings.scoring,
                         duration_s=(bank.blueprint.duration_minutes * 60) if (mode == "exam" or timed) else 0,
                         tasks=[s.to_json() for s in selected],
                         forgive_downtime=self.settings.forgive_downtime,
                         show_difficulty=self.settings.show_difficulty_during_exam or mode == "practice",
                         warnings_minutes=list(self.settings.warnings_minutes),
                         bank_digest=bank_digest(exam),
                         box=box.manifest(self.settings, self.settings.provider) or {})
        lab = self.lab(exam)
        anchors = {bank.tasks[t["task"]].anchor for t in sess.tasks}
        for name in lab.names():
            if lab.vm(name).spec.role == "utility":
                sess.passwords[name] = secrets_util.password()
                continue
            pw = secrets_util.password()
            sess.passwords[name] = pw
            if not (name == "node2" and "root-reset" in anchors):
                sess.given[name] = pw
        sess.broken_nodes = sorted({bank.tasks[t["task"]].node for t in sess.tasks
                                    if bank.tasks[t["task"]].breaks_boot})
        sess.save()
        sess.event("created", seed=seed, tasks=[t["task"] for t in sess.tasks])
        S.set_current(sess)
        return sess

    # --- preparing the lab for a session -------------------------------------------------------
    def prepare(self, sess: S.Session, *, on_step: StepFn | None = None, on_line: LineFn | None = None,
                cancel: threading.Event | None = None) -> None:
        step = on_step or (lambda s: None)
        bank = self.bank(sess.exam)
        lab = self.lab(sess.exam)
        sess.transition(S.PROVISIONING)
        try:
            self._ensure_baseline(lab, step, on_line, cancel)
            step("Restoring a clean lab")
            lab.revert(BASELINE)
            lab.start_all()
            missing = lab.wait_all(timeout=600)
            if missing:
                raise EngineError(f"{', '.join(missing)} did not start", "Try again; if it persists: Lab → Rebuild.")
            step("Preparing this exam's starting point")
            self._apply_setups(sess, bank, lab, step, on_line)
            step("Saving the exam starting point (for Reset node / Retake)")
            lab.snapshot_all(EXAM_START, f"session {sess.id}")
            lab.start_all()
            healthy = [n for n in lab.names() if n not in sess.broken_nodes]
            missing = lab.wait_all(healthy, timeout=600)
            if missing:
                raise EngineError(f"{', '.join(missing)} did not start after setup")
        except (LabError, EngineError, remote.SSHConfigError) as exc:
            sess.transition(S.PROVISION_FAILED, error=str(exc))
            raise
        except Exception as exc:  # unexpected: keep the session recoverable
            _log.exception("prepare failed")
            sess.transition(S.PROVISION_FAILED, error=repr(exc))
            raise
        sess.transition(S.READY)

    def _ensure_baseline(self, lab: Lab, step: StepFn, line: LineFn | None, cancel: threading.Event | None) -> None:
        st = lab.state()
        other = "rhce" if lab.exam == "rhcsa" else "rhcsa"
        other_lab = self.lab(other)
        if other_lab.exists():
            step(f"Removing the {other.upper()} lab (only one lab at a time)")
            other_lab.destroy()
        fresh = (not lab.exists() or st.get("phase") not in ("baseline", "ready")
                 or st.get("profile") != self.settings.profile
                 or not all(BASELINE in lab.hv.snapshots(v.domain) for v in lab.vms))
        if fresh:
            if lab.exists():
                step("Rebuilding the lab")
                lab.destroy()
            lab.up(root_passwords={n: secrets_util.password() for n in lab.names()}, on_step=step,
                   on_line=line, cancel=cancel)
            step("Saving the clean lab (baseline snapshot)")
            lab.snapshot_all(BASELINE, "clean provisioned lab")
            lab.save_state(phase="baseline")

    def _apply_setups(self, sess: S.Session, bank: Bank, lab: Lab, step: StepFn, line: LineFn | None) -> None:
        facts = lab.facts()
        lib = self._setup_lib()
        # By IP address: a task may break name resolution (DNS drills) before a later setup,
        # or a practice drill, needs packages.
        base = f"http://{facts['utility']['ip']}/rhel10"
        repo = (f"[setup-BaseOS]\nname=setup\nbaseurl={base}/BaseOS\ngpgcheck=1\n"
                f"gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release\n"
                f"[setup-AppStream]\nname=setup\nbaseurl={base}/AppStream\ngpgcheck=1\n"
                f"gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release\n")
        exam_nodes = [v.name for v in lab.vms if v.spec.role != "utility"]
        if sess.exam == "rhce":
            sess.accounts = lab.accounts()
            sess.save()
        # Prelude: passwords, a reminder banner, the Red Hat signing keys, temporary setup
        # repository (the RHCE control node keeps the lab.repo it was built with).
        # The keys are imported with rpm because dnf's own key parsing (libdnf keysFromFd on
        # RHEL 10.0) intermittently fails with "Parsing armored OpenPGP packet(s) failed", which
        # broke setups and would break a candidate's first `dnf install` the same way.
        for n in exam_nodes:
            script = (
                f"echo 'root:{sess.passwords[n]}' | chpasswd\n"
                "rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release\n"
                f"cat > /etc/motd <<'EOF'\n"
                f"autorelabel {sess.exam.upper()} lab node. Do not modify the 'mgmt0' interface or the\n"
                f"'vagrant' account: they are how your work gets graded.\nEOF\n"
            )
            if lab.vm(n).spec.role != "control":
                script += f"cat > {SETUP_REPO} <<'EOF'\n{repo}EOF\n"
            res = remote.run_script(lab.target(n), script, timeout=60)
            if not res.ok:
                raise EngineError(f"could not prepare {n}: {res.tail(3)}")
        # Task setups: regular tasks first, anchors last (the network anchor removes connectivity).
        entries = sorted(sess.tasks, key=lambda e: (bool(bank.tasks[e["task"]].anchor), e["number"]))
        for e in entries:
            task = bank.tasks[e["task"]]
            for node, script in [(n, sc) for target, sc in task.setup_scripts.items()
                                 for n in labfacts.script_nodes(target, facts)]:
                step(f"Task {e['number']}: preparing {node}")
                env = {**render.env_for(e["params"], facts), "AR_NODE": node, "AR_TASK": task.id}
                res = remote.run_script(lab.target(node), lib + "\n" + script.read_text(), env=env, timeout=900)
                if line:
                    for out_line in (res.out + res.err).splitlines():
                        line(f"[{node}] {out_line}")
                if not res.ok:
                    raise EngineError(f"setup of task {e['number']} ({task.id}) failed on {node}", res.tail(5))
        # Practice: prerequisites the drill doesn't include are solved for you (RHCE: Ansible
        # configuration and SSH access), so one task can be practised on its own.
        if sess.mode != "exam":
            present = {bank.tasks[e["task"]].anchor for e in sess.tasks}
            for anchor in bank.blueprint.practice_prereqs:
                task = next((t for t in bank.tasks.values() if t.anchor == anchor), None)
                if anchor in present or task is None:
                    continue
                step(f"Setting up the prerequisite: {task.title}")
                params = practice(bank, [task.id], sess.seed)[0].params
                for node, script in [(n, sc) for target, sc in task.solution_scripts.items()
                                     for n in labfacts.script_nodes(target, facts)]:
                    env = {**render.env_for(params, facts), "AR_NODE": node, "AR_TASK": task.id,
                           **{f"AR_{u.upper()}_PASSWORD": pw for u, pw in sess.accounts.items()}}
                    res = remote.run_script(lab.target(node), lib + "\n" + script.read_text(), env=env,
                                            timeout=900)
                    if not res.ok:
                        raise EngineError(f"prerequisite {task.id} failed on {node}", res.tail(5))
        # Exams always include the "configure repositories" anchor, so nodes start without any.
        # Practice sessions that don't include it keep working repositories, so a single-task
        # drill is never blocked by an unrelated objective.
        has_repo_anchor = any(bank.tasks[e["task"]].anchor == "repos" for e in sess.tasks)
        for n in exam_nodes:
            if lab.vm(n).spec.role == "control":
                continue
            if has_repo_anchor or sess.mode == "exam":
                cmd = f"rm -f {SETUP_REPO}"
            else:
                cmd = (f"sed 's/^\\[setup-/[/; s/^name=setup/name=lab/' {SETUP_REPO} "
                       f"> /etc/yum.repos.d/lab.repo; rm -f {SETUP_REPO}")
            remote.run_script(lab.target(n), cmd + "; dnf clean all >/dev/null 2>&1 || true\n", timeout=60)

    # --- the exam itself -----------------------------------------------------------------------
    def start(self, sess: S.Session) -> None:
        if sess.state != S.READY:
            raise EngineError(f"cannot start from state {sess.state}")
        sess.started = time.time()
        sess.transition(S.IN_PROGRESS)
        sess.tick()
        if sess.duration_s:
            self.launch_proctor(sess)

    def launch_proctor(self, sess: S.Session) -> None:
        unit = f"autorelabel-proctor-{sess.id}"
        python = sys.executable
        envs = {"PYTHONPATH": str(paths.ROOT / "src"), "AUTORELABEL_ROOT": str(paths.ROOT),
                "PYTHONPYCACHEPREFIX": str(paths.WORKSPACE / "pycache")}
        if shutil.which("systemd-run") and self._systemd_user_ok():
            ledger.record("systemd-unit", unit, "proctor (transient)", storage_dir=self.settings.storage_dir)
            cmd = ["systemd-run", "--user", "--quiet", "--collect", f"--unit={unit}",
                   f"--working-directory={paths.ROOT}"]
            cmd += [f"--setenv={k}={v}" for k, v in envs.items()]
            cmd += [python, "-m", "autorelabel", "proctor", sess.id]
            res = proc.run(cmd, timeout=30)
            if res.ok:
                sess.event("proctor_started", how="systemd-run", unit=unit)
                return
            _log.warning("systemd-run failed (%s); falling back to a detached process", res.tail(2))
        import subprocess

        logf = open(paths.LOGS / f"proctor-{sess.id}.log", "a")
        subprocess.Popen([python, "-m", "autorelabel", "proctor", sess.id], cwd=paths.ROOT,
                         env={**os.environ, **envs}, stdin=subprocess.DEVNULL, stdout=logf, stderr=logf,
                         start_new_session=True)
        sess.event("proctor_started", how="detached")

    @staticmethod
    def _systemd_user_ok() -> bool:
        res = proc.run(["systemctl", "--user", "is-system-running"], timeout=10)
        return res.out.strip() in ("running", "degraded")

    def proctor_alive(self, sess: S.Session) -> bool:
        hb = sess.heartbeat()
        return bool(hb) and hb.get("boot_id") == S.boot_id() and time.time() - float(hb.get("wall", 0)) < 30

    def lock(self, sess: S.Session, reason: str = "time") -> None:
        if sess.state not in (S.IN_PROGRESS, S.INTERRUPTED):
            return
        sess.ended = time.time()
        sess.transition(S.LOCKED, reason=reason)
        self.close_code_server(sess)
        lab = self.lab(sess.exam)
        lab.pause_all()

    def grade(self, sess: S.Session, on_event: Callable[[str, dict[str, Any]], None] | None = None,
              *, official: bool = True, reboot: bool = True) -> dict[str, Any]:
        bank = self.bank(sess.exam)
        lab = self.lab(sess.exam)
        if official:
            if sess.state == S.LOCKED or sess.state == S.GRADING_INTERRUPTED:
                sess.transition(S.GRADING)
            elif sess.state != S.GRADING:
                raise EngineError(f"cannot grade from state {sess.state}")
        try:
            g = Grader(sess, lab, bank, on_event)
            if not official:
                g.checkpoint_file = fresh_checkpoint(sess.dir)
            results = g.grade(reboot=reboot)
        except Exception:
            if official:
                sess.transition(S.GRADING_INTERRUPTED)
            raise
        if official:
            write_report(sess, bank, results)
            sess.transition(S.GRADED, score=results["scaled_score"], passed=results["passed"])
        return results

    def submit(self, sess: S.Session) -> None:
        """End the exam early: lock now; the proctor (or caller) grades."""
        self.lock(sess, reason="submitted")

    def abandon(self, sess: S.Session) -> None:
        self.close_code_server(sess)
        if sess.state != S.ABANDONED:
            sess.transition(S.ABANDONED)
        S.set_current(None)

    def retake(self, sess: S.Session) -> S.Session:
        """Same tasks, same parameters, back to the exam starting point."""
        lab = self.lab(sess.exam)
        new = S.Session(**{**{k: getattr(sess, k) for k in S.Session.__dataclass_fields__},
                           "id": S.new_id(), "created": time.time(), "state": S.NEW, "marks": {},
                           "started": None, "ended": None, "incidents": [], "code_port": 0})
        new.save()
        new.event("retake_of", session=sess.id)
        new.transition(S.PROVISIONING)
        lab.revert(EXAM_START)
        lab.start_all()
        lab.wait_all([n for n in lab.names() if n not in new.broken_nodes], timeout=600)
        new.transition(S.READY)
        S.set_current(new)
        return new

    # --- recovery after crashes / reboots -------------------------------------------------------
    def recover(self, sess: S.Session) -> str:
        """Bring a session back to a consistent state when the app starts. Returns a
        short description of what was done (or "")."""
        if sess.state == S.IN_PROGRESS:
            hb = sess.heartbeat()
            if hb and hb.get("boot_id") != S.boot_id():
                sess.transition(S.INTERRUPTED, why="host rebooted")
                return "The host restarted during your exam. Downtime is not counted. Resume when ready."
            if sess.duration_s and sess.remaining() <= 0:
                self.lock(sess, reason="time")
                return "Time ran out while autorelabel was closed. Your exam has been locked for grading."
            if sess.duration_s and not self.proctor_alive(sess):
                self.launch_proctor(sess)
                return "Restarted the exam proctor."
        if sess.state == S.GRADING and not self.proctor_alive(sess):
            sess.transition(S.GRADING_INTERRUPTED)
            return "Grading was interrupted; it will resume where it stopped."
        if sess.state == S.PROVISIONING:
            sess.transition(S.PROVISION_FAILED, error="interrupted")
            return "Lab preparation was interrupted. Retry to continue."
        return ""

    def resume(self, sess: S.Session) -> None:
        """INTERRUPTED (host reboot) → IN_PROGRESS: start the lab again without re-provisioning."""
        lab = self.lab(sess.exam)
        lab.prepare_host()
        lab.start_all()
        lab.wait_all([n for n in lab.names() if n not in sess.broken_nodes], timeout=600)
        sess.transition(S.IN_PROGRESS)
        sess.tick()
        if sess.duration_s:
            self.launch_proctor(sess)

    # --- node controls ---------------------------------------------------------------------------
    def power_on(self, sess: S.Session, node: str) -> None:
        self.lab(sess.exam).start_all([node])
        sess.event("power_on", node=node)

    def reset(self, sess: S.Session, node: str) -> None:
        lab = self.lab(sess.exam)
        lab.hv.reset(lab.vm(node).domain)
        sess.event("reset", node=node)

    def reset_to_start(self, sess: S.Session, node: str) -> None:
        lab = self.lab(sess.exam)
        lab.revert(EXAM_START, [node])
        lab.start_all([node])
        sess.incident(node, "reset-to-start", "was reset to the exam starting point by the candidate")

    # --- presentation helpers -----------------------------------------------------------------------
    def selected(self, sess: S.Session) -> list[SelectedTask]:
        bank = self.bank(sess.exam)
        return [SelectedTask(t["number"], bank.tasks[t["task"]], t["params"], t["points"]) for t in sess.tasks]

    def rendered(self, sess: S.Session) -> list[dict[str, Any]]:
        lab = self.lab(sess.exam)
        facts = lab.facts()
        out = []
        for s in self.selected(sess):
            ctx = {**s.params, "lab": facts}
            out.append({
                "number": s.number, "id": s.task.id, "title": render.render(s.task.title, ctx),
                "prompt": render.render(s.task.prompt, ctx), "difficulty": s.task.difficulty,
                "points": s.points, "node": s.task.node, "estimated_minutes": s.task.estimated_minutes,
                "console_only": s.task.console_only,
            })
        return out

    def candidate_info(self, sess: S.Session) -> dict[str, Any]:
        lab = self.lab(sess.exam)
        facts = lab.facts()
        nodes = []
        for v in lab.vms:
            if v.spec.role == "utility":
                continue
            nodes.append({"name": v.name, "fqdn": v.spec.fqdn, "ip": v.lab_ip,
                          "root_password": sess.given.get(v.name), "domain": v.domain,
                          "nic": facts[v.name].get("nic", "")})
        info: dict[str, Any] = {
            "exam": sess.exam, "nodes": nodes, "domain": labfacts.DOMAIN, "utility": facts["utility_fqdn"],
            "repo_baseos": facts["repo_baseos"], "repo_appstream": facts["repo_appstream"],
            "network": facts["network"], "gateway": facts["gateway"], "dns": facts["dns"]}
        if sess.exam == "rhce":
            ctl = lab.vm("control")
            info["accounts"] = dict(sess.accounts)
            info["control"] = {"fqdn": ctl.spec.fqdn, "ip": ctl.lab_ip, "user": labfacts.CONTROL_USER,
                               "project_dir": facts["project_dir"]}
            info["inventory_md"] = facts["inventory_md"]
            info["git_url"] = facts["git_url"]
            info["code_server"] = self.code_server_url(sess) if self.settings.code_server else ""
        return info

    def code_server_url(self, sess: S.Session) -> str:
        """code-server through an SSH tunnel on 127.0.0.1: browsers only give the clipboard,
        web views and service workers to secure contexts (HTTPS or localhost), and the lab
        address is plain HTTP. Falls back to the lab address if the tunnel can't be opened."""
        ctl = self.lab(sess.exam).vm("control")
        direct = f"http://{ctl.lab_ip}:8080"
        if sess.state not in (S.READY, S.IN_PROGRESS, S.INTERRUPTED):
            return direct
        label = f"code-{sess.id}"
        try:
            if not (sess.code_port and remote.tunnel_alive(label)):
                port = remote.free_local_port(sess.code_port or CODE_SERVER_LOCAL_PORT)
                if not remote.open_tunnel(self.lab(sess.exam).target("control"), label, port, 8080):
                    return direct
                if port != sess.code_port:
                    sess.code_port = port
                    sess.save()
        except OSError:
            return direct
        return f"http://127.0.0.1:{sess.code_port}/?folder={labfacts.PROJECT_DIR}"

    @staticmethod
    def close_code_server(sess: S.Session) -> None:
        if sess.exam == "rhce":
            remote.close_tunnel(f"code-{sess.id}")

    def solutions(self, sess: S.Session) -> dict[int, str]:
        out = {}
        for s in self.selected(sess):
            md = s.task.solution_md.read_text(encoding="utf-8") if s.task.solution_md.exists() else ""
            ctx = {**s.params, "lab": self.lab(sess.exam).facts()}
            try:
                md = render.render(md, ctx)
            except render.RenderError:
                pass
            out[s.number] = md
        return out
