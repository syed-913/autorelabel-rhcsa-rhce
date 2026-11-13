"""An Exam Desk with no lab behind it, to look at the page in a browser.

    PYTHONPATH=src python scripts/dev/demo/desk_demo.py <empty folder> [--port N]

It writes a session with a real generated RHCSA exam into the folder and starts the desk on it.
The "nodes" are local shells with a neutral prompt in a scratch folder: nothing reaches a VM, and
the clock is a plain session that runs out after three hours. For the website's recording of the
Exam Desk use a real lab; this is for checking the page itself.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import time
from pathlib import Path
from types import SimpleNamespace

from autorelabel import labfacts, paths
from autorelabel import session as S
from autorelabel.bank import load_bank, render
from autorelabel.bank.select import generate
from autorelabel.desk.server import Desk


class DemoEngine:
    def __init__(self, sess: S.Session):
        bank = load_bank(sess.exam)
        facts = labfacts.sample(sess.exam)
        self.tasks = []
        for s in generate(bank, sess.seed):
            ctx = {**s.params, "lab": facts}
            self.tasks.append({"number": s.number, "title": render.render(s.task.title, ctx),
                               "prompt": render.render(s.task.prompt, ctx), "difficulty": s.task.difficulty,
                               "points": s.points, "node": s.task.node, "console_only": s.task.console_only})
        vms = [SimpleNamespace(name=n, spec=SimpleNamespace(role="node", fqdn=f"{n}.lab.example.com"),
                               lab_ip=ip, domain=f"demo-{n}") for n, ip in (("node1", "172.25.250.11"),
                                                                            ("node2", "172.25.250.12"))]
        self._lab = SimpleNamespace(vms=vms, hv=SimpleNamespace(state=lambda domain: ("running", "")))

    def rendered(self, sess):
        return self.tasks

    def lab(self, exam):
        return self._lab

    def console_login(self, sess, node):
        if node == "node1":
            return "Log in as root, password: redhat"
        return "Its root password is not given: see the tasks"

    def proctor_alive(self, sess):
        return True

    def start(self, sess):
        sess.started = time.time()
        sess.transition(S.IN_PROGRESS)

    def submit(self, sess):
        sess.ended = time.time()
        sess.transition(S.LOCKED, reason="submitted")

    def lock(self, sess, reason="time"):
        self.submit(sess)

    def reset_to_start(self, sess, node):
        time.sleep(2)

    def code_server_url(self, sess):
        return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--port", type=int, default=0)
    args = ap.parse_args()
    root = args.folder.resolve()
    paths.SESSIONS = root / "sessions"
    home = root / "home"
    home.mkdir(parents=True, exist_ok=True)
    sess = S.Session(id="demo-desk", exam="rhcsa", mode="exam", seed=4242, created=time.time(), state=S.IN_PROGRESS,
                     duration_s=3 * 3600, started=time.time() - 2400)
    sess.dir.mkdir(parents=True, exist_ok=True)
    sess.save()
    engine = DemoEngine(sess)

    def spawn(kind: str, node: str, _sess) -> tuple[list[str], str]:
        prompt = f"[root@{node} ~]# "
        return (["env", "-i", f"PATH={os.environ.get('PATH', '/usr/bin:/bin')}", f"HOME={home}", "TERM=xterm-256color",
                 f"PS1={prompt}", "bash", "--noprofile", "--norc", "-i"],
                f"Demo {'console' if kind == 'console' else 'shell'} for {node}: a local shell, no VM.")

    desk = Desk(args.port, engine=engine, spawn_argv=spawn, session_loader=lambda: S.load(sess.id))

    def ready(d: Desk) -> None:
        print(f"Exam Desk (demo): {d.url}\nCode: {d.code}", flush=True)

    os.chdir(home)
    try:
        asyncio.run(desk.run(ready))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
