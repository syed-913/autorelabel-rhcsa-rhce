"""Subcommands beyond doctor/banner/config (box, lab, exam, grading...)."""

from __future__ import annotations

import argparse
import json
import sys

from . import config


def _err(msg: str, hint: str = "") -> int:
    print(f"error: {msg}", file=sys.stderr)
    if hint:
        print(f"hint: {hint}", file=sys.stderr)
    return 1


def _fail(exc: BaseException, what: str, exam: str = "") -> int:
    """An operation failed: show the error and its hint and, unless it is the user's to fix,
    write a problem report and say where to post it."""
    from . import report

    hint = getattr(exc, "hint", "") or ""
    log_file = getattr(exc, "log_file", None)
    if log_file:
        print(f"log: {log_file}", file=sys.stderr)
    _err(report.describe(exc), hint)
    if report.reportable(exc):
        path = report.write(what, report.describe(exc), hint=hint, log_file=log_file, exc=exc, exam=exam)
        report.print_notice(path, has_hint=bool(hint))
    return 1


def _printer(indent: str = "    "):
    """Prints a tool's output lines. A progress counter redraws one terminal line instead of
    adding a line per value (and is left out when the output is not a terminal)."""
    from . import proc

    tty = sys.stdout.isatty()
    drawn = [""]                        # the counter value on screen

    def out(s: str) -> None:
        if isinstance(s, proc.Progress):
            if tty:
                print(f"\r\x1b[K{indent}{s}", end="", flush=True)
                drawn[0] = s
            return
        if drawn[0]:
            print()                     # the counter's last value stays on its line
            if s == drawn[0]:
                drawn[0] = ""
                return
            drawn[0] = ""
        print(f"{indent}{s}", flush=True)

    return out


def cmd_box_build(args: argparse.Namespace) -> int:
    from . import box

    settings = config.load()
    provider = args.provider or settings.provider
    if not provider:
        return _err("no provider chosen", "run: ./autorelabel config provider=libvirt")
    if not settings.storage_dir or not settings.iso_path:
        return _err("lab storage directory or ISO not configured", "run ./autorelabel (setup wizard)")

    def step(s: str) -> None:
        print(f"==> {s}", flush=True)

    try:
        log_file = box.build(settings, provider, on_line=_printer() if args.verbose else None, on_step=step)
    except box.BoxError as exc:
        return _fail(exc, f"Building the {provider} box")
    print(f"Box ready. Log: {log_file}")
    return 0


def cmd_box_status(_args: argparse.Namespace) -> int:
    from . import box

    settings = config.load()
    for provider in ("libvirt", "virtualbox"):
        ok, msg = box.box_status(settings, provider)
        print(f"{provider:11} {'ready' if ok else '-':6} {msg}")
    return 0


def cmd_bank_lint(args: argparse.Namespace) -> int:
    from .bank import coverage, lint, load_bank

    rc = 0
    for exam in args.exams:
        bank = load_bank(exam)
        issues = lint.lint_bank(bank)
        errors = [i for i in issues if i.severity == "error"]
        for i in issues:
            if i.severity == "error" or args.warnings:
                print(i)
        gate = coverage.gate_failures(bank, args.gate)
        for g in gate:
            print(f"COVERAGE {exam}: {g}")
        s = coverage.summary(bank)
        print(f"{exam}: {s['tasks']} tasks, {len(errors)} error(s), primary {s['objectives_with_primary']}/"
              f"{s['objectives']}, facets {s['facets_covered']}/{s['facets']}, gate "
              f"{args.gate or bank.blueprint.coverage_gate}: {'FAIL' if gate else 'ok'}")
        if errors or gate:
            rc = 1
    return rc


def cmd_bank_coverage(args: argparse.Namespace) -> int:
    from . import paths
    from .bank import coverage, load_bank

    bank = load_bank(args.exam)
    text = coverage.markdown(bank)
    out = paths.ROOT / "docs" / f"COVERAGE-{args.exam.upper()}.md"
    readme = paths.ROOT / "README.md"
    if args.write:
        out.write_text(text, encoding="utf-8")
        readme.write_text(coverage.update_readme(readme.read_text(encoding="utf-8"), bank), encoding="utf-8")
        print(f"wrote {out} and the {args.exam.upper()} objectives in {readme.name}")
    elif args.check:
        for f, want in ((out, text), (readme, coverage.update_readme(readme.read_text(encoding="utf-8"), bank))):
            if not f.exists() or f.read_text(encoding="utf-8") != want:
                return _err(f"{f.name} is stale", f"run ./autorelabel bank coverage {args.exam} --write")
        print(f"{out.name} and the {args.exam.upper()} objectives in {readme.name} are up to date")
    else:
        print(text)
    return 0


def cmd_bank_sample(args: argparse.Namespace) -> int:
    from . import labfacts
    from .bank import load_bank, render
    from .bank.select import generate

    bank = load_bank(args.exam)
    exam = generate(bank, args.seed)
    if args.json:
        print(json.dumps([s.to_json() for s in exam], indent=2))
        return 0
    lab = labfacts.sample(args.exam)
    total = 0
    for s in exam:
        total += s.points
        text = render.render(s.task.prompt, {**s.params, "lab": lab})
        print(f"\nTask {s.number} [{s.task.difficulty}, {s.points} pts] {s.task.title}  ({s.task.id})")
        print("  " + text.replace("\n", "\n  "))
    print(f"\nTotal: {total} points")
    return 0


def _lab(exam: str):
    from .lab import Lab

    settings = config.load()
    if not settings.configured:
        raise SystemExit("error: run ./autorelabel first to complete setup (provider, storage, ISO)")
    return Lab(settings, exam)


def cmd_lab_up(args: argparse.Namespace) -> int:
    from . import secrets_util
    from .lab import LabError

    if args.exam == "rhce" and _ensure_rhce_content(args.verbose):
        return 1
    lab = _lab(args.exam)
    pw = {n: secrets_util.password() for n in lab.names()}
    try:
        log_file = lab.up(root_passwords=pw, on_step=lambda s: print(f"==> {s}", flush=True),
                          on_line=_printer() if args.verbose else None)
    except LabError as exc:
        return _fail(exc, f"Bringing up the {args.exam.upper()} lab", args.exam)
    print(f"Lab is up. Log: {log_file}")
    return 0


def cmd_lab_status(args: argparse.Namespace) -> int:
    lab = _lab(args.exam)
    for name, (st, reason) in lab.power_states().items():
        v = lab.vm(name)
        print(f"{name:8} {st:10} {reason:12} mgmt {v.mgmt_ip:16} lab {v.lab_ip}")
    return 0


def cmd_lab_health(args: argparse.Namespace) -> int:
    problems = _lab(args.exam).health_check()
    for p in problems:
        print(p)
    print("healthy" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def cmd_lab_destroy(args: argparse.Namespace) -> int:
    _lab(args.exam).destroy(on_line=_printer())
    print("Lab destroyed (networks, pool and box are kept; use uninstall to remove everything).")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
    register_exam(sub)
    register_selftest(sub)
    register_content(sub)
    lab = sub.add_parser("lab", help="bring the lab VMs up, inspect or destroy them")
    lsub = lab.add_subparsers(dest="lab_cmd", required=True)
    lu = lsub.add_parser("up", help="create and provision the lab (no exam tasks)")
    lu.add_argument("exam", choices=("rhcsa", "rhce"))
    lu.add_argument("-v", "--verbose", action="store_true")
    lu.set_defaults(func=cmd_lab_up)
    for name, fn, hlp in (("status", cmd_lab_status, "power state of each VM"),
                          ("health", cmd_lab_health, "check lab services"),
                          ("destroy", cmd_lab_destroy, "delete the lab VMs")):
        p = lsub.add_parser(name, help=hlp)
        p.add_argument("exam", choices=("rhcsa", "rhce"), nargs="?", default="rhcsa")
        p.set_defaults(func=fn)

    b = sub.add_parser("box", help="build or inspect the RHEL 10 Vagrant box")
    bsub = b.add_subparsers(dest="box_cmd", required=True)
    bb = bsub.add_parser("build", help="build the box from your ISO (about 15 min)")
    bb.add_argument("--provider", choices=("libvirt", "virtualbox"))
    bb.add_argument("-v", "--verbose", action="store_true", help="show the full Packer output")
    bb.set_defaults(func=cmd_box_build)
    bs = bsub.add_parser("status", help="show box status")
    bs.set_defaults(func=cmd_box_status)

    k = sub.add_parser("bank", help="task bank tools (lint, coverage, sample exam)")
    ksub = k.add_subparsers(dest="bank_cmd", required=True)
    kl = ksub.add_parser("lint", help="lint tasks and enforce the coverage gate")
    kl.add_argument("exams", nargs="*", default=["rhcsa", "rhce"])
    kl.add_argument("--gate", choices=("none", "wave1", "full"))
    kl.add_argument("--warnings", action="store_true")
    kl.set_defaults(func=cmd_bank_lint)
    kc = ksub.add_parser("coverage", help="objective coverage report (docs/COVERAGE-<EXAM>.md)")
    kc.add_argument("exam", choices=("rhcsa", "rhce"))
    kc.add_argument("--write", action="store_true")
    kc.add_argument("--check", action="store_true")
    kc.set_defaults(func=cmd_bank_coverage)
    ks = ksub.add_parser("sample", help="print a generated exam for a seed")
    ks.add_argument("exam", choices=("rhcsa", "rhce"))
    ks.add_argument("--seed", type=int, default=1)
    ks.add_argument("--json", action="store_true")
    ks.set_defaults(func=cmd_bank_sample)


# --- exam flow -----------------------------------------------------------------------------------

def _engine():
    from .engine import Engine

    return Engine()


def _current():
    from . import session as S

    sess = S.current()
    if sess is None:
        raise SystemExit("error: no exam in progress (start one with: ./autorelabel exam start rhcsa)")
    return sess


def _fmt_time(seconds: float) -> str:
    seconds = int(max(0, seconds))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _ensure_rhce_content(verbose: bool = False) -> int:
    """The one-time RHCE download (as the TUI does before an RHCE exam). Returns 1 on failure."""
    from . import content

    st = config.load()
    ok, _msg = content.status(st)
    if ok:
        return 0
    print("The RHCE lab needs ansible-navigator, the ansible.posix and community.general collections"
          + (" and code-server (VS Code in the browser)" if st.code_server else "") + ". Downloading them once"
          " (about 60-150 MB); everything after that works offline.", flush=True)
    try:
        content.download(st, on_line=_printer() if verbose else None,
                         on_step=lambda s: print(f"==> {s}", flush=True), with_code_server=st.code_server)
    except content.ContentError as exc:
        return _fail(exc, "Downloading the RHCE content", "rhce")
    return 0


def cmd_exam_start(args: argparse.Namespace) -> int:
    from .engine import EngineError
    from .lab import LabError

    eng = _engine()
    if args.exam == "rhce" and _ensure_rhce_content(args.verbose):
        return 1
    try:
        sess = eng.create(args.exam, mode="exam", seed=args.seed)
        print(f"Session {sess.id} (seed {sess.seed}): preparing the lab...")
        eng.prepare(sess, on_step=lambda s: print(f"==> {s}", flush=True),
                    on_line=_printer() if args.verbose else None)
    except (EngineError, LabError) as exc:
        return _fail(exc, f"Preparing an {args.exam.upper()} exam", args.exam)
    if args.no_start:
        print("Lab ready. Start the timer with: ./autorelabel exam begin")
        return 0
    eng.start(sess)
    print(f"Exam started: {sess.duration_s // 60} minutes. Tasks: ./autorelabel exam tasks")
    return 0


def cmd_exam_begin(_args: argparse.Namespace) -> int:
    eng = _engine()
    sess = _current()
    eng.start(sess)
    print(f"Exam started: {sess.duration_s // 60} minutes.")
    return 0


def cmd_exam_tasks(args: argparse.Namespace) -> int:
    eng = _engine()
    sess = _current()
    info = eng.candidate_info(sess)
    print(f"{sess.exam.upper()} exam · session {sess.id} · state {sess.state}")
    for n in info["nodes"]:
        pw = n["root_password"] or "(unknown: see the tasks)"
        print(f"  {n['name']:7} {n['fqdn']:24} {n['ip']:15} root password: {pw}")
    if info["exam"] == "rhce":   # what the TUI's instructions show: without it, no way into control
        acc, ctl = info["accounts"], info["control"]
        print(f"\n  Work on control as {ctl['user']} (password {acc.get('student', '?')}) in {ctl['project_dir']}:"
              f" ./autorelabel ssh control")
        print(f"  Managed nodes have a user ansible (password {acc.get('ansible', '?')}).")
        print(f"  Git repository: {info['git_url']} (user {ctl['user']}, same password)")
        if info.get("code_server"):
            print(f"  VS Code in your browser: {info['code_server']} (password: the {ctl['user']} password)")
        print("  Inventory groups:")
        for line in info["inventory_md"].splitlines():
            print("    " + line.replace("`", "").replace("**", ""))
    for t in eng.rendered(sess):
        diff = f" [{t['difficulty']}]" if sess.show_difficulty else ""
        print(f"\nTask {t['number']} ({t['points']} pts){diff}: {t['title']}")
        print("  " + t["prompt"].replace("\n", "\n  "))
    return 0


def cmd_exam_status(_args: argparse.Namespace) -> int:
    eng = _engine()
    sess = _current()
    note = eng.recover(sess)
    if note:
        print(note)
    print(f"session {sess.id}  exam {sess.exam}  state {sess.state}")
    if sess.duration_s:
        print(f"time remaining {_fmt_time(sess.remaining())} of {_fmt_time(sess.duration_s)}"
              f"  proctor {'running' if eng.proctor_alive(sess) else 'not running'}")
    return 0


def cmd_exam_timer(args: argparse.Namespace) -> int:
    from . import timer

    sess = _current()
    return timer.once(sess) if args.once else timer.run(sess.id, compact=args.compact)


def cmd_exam_submit(_args: argparse.Namespace) -> int:
    eng = _engine()
    sess = _current()
    eng.submit(sess)
    if not eng.proctor_alive(sess):
        return cmd_exam_grade(_args)
    print("Exam locked; the proctor is grading it. Watch: ./autorelabel exam status")
    return 0


def cmd_exam_grade(_args: argparse.Namespace) -> int:
    from . import session as S

    eng = _engine()
    sess = _current()
    if sess.state in (S.IN_PROGRESS, S.INTERRUPTED):
        eng.lock(sess, reason="manual")

    def ev(kind: str, data: dict) -> None:
        if kind == "phase":
            print(f"==> {data['label']}", flush=True)
        elif kind == "reboot":
            print(f"    {data['node']}: {data['stage']} {data.get('message', '')}", flush=True)

    results = eng.grade(sess, ev)
    print(sess.report_file.read_text())
    return 0 if results["passed"] else 3


def cmd_exam_results(args: argparse.Namespace) -> int:
    from . import session as S

    sess = S.load(args.session) if args.session else _current()
    if not sess.report_file.exists():
        return _err("this session has not been graded yet")
    print(sess.report_file.read_text())
    if args.solutions:
        for number, md in _engine().solutions(sess).items():
            print(f"\n---\n## Solution {number}\n\n{md}")
    return 0


def cmd_exam_retake(_args: argparse.Namespace) -> int:
    eng = _engine()
    new = eng.retake(_current())
    print(f"Retake ready: session {new.id}. Start with: ./autorelabel exam begin")
    return 0


def cmd_exam_resume(_args: argparse.Namespace) -> int:
    eng = _engine()
    sess = _current()
    eng.resume(sess)
    print("Resumed.")
    return 0


def cmd_exam_abandon(_args: argparse.Namespace) -> int:
    _engine().abandon(_current())
    print("Session abandoned.")
    return 0


def _lab_ip(node: str) -> tuple[str, str]:
    sess = _current()
    eng = _engine()
    lab = eng.lab(sess.exam)
    v = lab.vm(node)
    return v.lab_ip, v.domain


def cmd_ssh(args: argparse.Namespace) -> int:
    import os

    from . import session as S

    sess = _current()
    if sess.state in (S.LOCKED, S.GRADING):
        return _err("the exam is locked: time is up")
    ip, _dom = _lab_ip(args.node)
    user = args.user or ("student" if sess.exam == "rhce" and args.node == "control" else "root")
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
           f"{user}@{ip}"]
    os.execvp("ssh", cmd)
    return 0


def cmd_console(args: argparse.Namespace) -> int:
    import os

    from . import session as S

    sess = _current()
    if sess.state in (S.LOCKED, S.GRADING):
        return _err("the exam is locked: time is up")
    _ip, dom = _lab_ip(args.node)
    eng = _engine()
    print(f"Serial console of {args.node}. {eng.console_login(sess, args.node)}\n"
          "Press Enter for a prompt; Ctrl+] to leave.", flush=True)
    cmd = eng.lab(sess.exam).hv.console_command(dom)
    os.execvp(cmd[0], cmd)
    return 0


def cmd_node(args: argparse.Namespace) -> int:
    eng = _engine()
    sess = _current()
    {"power-on": eng.power_on, "reset": eng.reset, "reset-to-start": eng.reset_to_start}[args.action](sess, args.node)
    print(f"{args.node}: {args.action} done")
    return 0


def cmd_proctor(args: argparse.Namespace) -> int:
    from . import proctor

    return proctor.run(args.session)


def register_exam(sub: argparse._SubParsersAction) -> None:
    e = sub.add_parser("exam", help="timed exams: start, tasks, submit, results, retake")
    esub = e.add_subparsers(dest="exam_cmd", required=True)
    es = esub.add_parser("start", help="generate a new exam, prepare the lab and start the timer")
    es.add_argument("exam", choices=("rhcsa", "rhce"))
    es.add_argument("--seed", type=int)
    es.add_argument("--no-start", action="store_true", help="prepare only; start the timer later")
    es.add_argument("-v", "--verbose", action="store_true")
    es.set_defaults(func=cmd_exam_start)
    for name, fn, hlp in (("begin", cmd_exam_begin, "start the timer of a prepared exam"),
                          ("tasks", cmd_exam_tasks, "show the task sheet"),
                          ("status", cmd_exam_status, "time remaining and state"),
                          ("submit", cmd_exam_submit, "end the exam now and grade it"),
                          ("grade", cmd_exam_grade, "grade now (normally the proctor does this)"),
                          ("retake", cmd_exam_retake, "same exam again from its starting point"),
                          ("resume", cmd_exam_resume, "resume after the host restarted"),
                          ("abandon", cmd_exam_abandon, "give up this session")):
        p = esub.add_parser(name, help=hlp)
        p.set_defaults(func=fn)
    et = esub.add_parser("timer", help="the time left, in big digits, for a terminal next to your work")
    et.add_argument("--compact", action="store_true", help="one line instead of big digits")
    et.add_argument("--once", action="store_true", help="print the time left once (for a tmux or shell status line)")
    et.set_defaults(func=cmd_exam_timer)
    er = esub.add_parser("results", help="show the graded report")
    er.add_argument("session", nargs="?")
    er.add_argument("--solutions", action="store_true")
    er.set_defaults(func=cmd_exam_results)

    s = sub.add_parser("ssh", help="ssh to a lab node as root (or --user)")
    s.add_argument("node")
    s.add_argument("--user", default=None, help="default: student on the RHCE control node, else root")
    s.set_defaults(func=cmd_ssh)
    c = sub.add_parser("console", help="attach to a node's serial console (Ctrl+] to leave)")
    c.add_argument("node")
    c.set_defaults(func=cmd_console)
    n = sub.add_parser("node", help="power controls for a lab node")
    n.add_argument("action", choices=("power-on", "reset", "reset-to-start"))
    n.add_argument("node")
    n.set_defaults(func=cmd_node)
    pr = sub.add_parser("proctor")   # internal: started by the engine
    pr.add_argument("session")
    pr.set_defaults(func=cmd_proctor)


def cmd_selftest(args: argparse.Namespace) -> int:
    from .selftest import SelfTest

    st = SelfTest(_engine(), args.exam, on_line=_printer(""))
    ids = None
    if args.tasks:
        ids = []
        for t in args.tasks:
            full = t if t.startswith(f"{args.exam}.") else f"{args.exam}.{t}"
            matches = [x for x in st.bank.tasks if x == full or x.startswith(full + ".") or x.startswith(full)]
            if not matches:
                return _err(f"no task matches {t!r}")
            ids.extend(matches)
    if args.sweep:
        sw = st.run_sweep(ids, only_changed=args.changed)
        bad = [f"{k} draw {d}" for k, draws in sw.items() if ids is None or k in ids
               for d, v in sorted(draws.items()) if v["status"] != "pass"]
        print(f"\n{len(bad)} draw(s) failing: " + ", ".join(bad) if bad else "\nevery value of every choice passes")
        return 1 if bad else 0
    res = st.run(ids, only_changed=args.changed)
    failed = [k for k, v in res.items() if v["status"] != "pass" and (ids is None or k in ids)]
    print(f"\n{len(failed)} task(s) failing self-test" if failed else "\nall selected tasks pass self-test")
    return 1 if failed else 0


def register_selftest(sub: argparse._SubParsersAction) -> None:
    s = sub.add_parser("selftest", help="verify tasks on real VMs (setup, solutions, mistakes)")
    s.add_argument("tasks", nargs="*", help="task ids or prefixes (e.g. security.selinux-port); default: all")
    s.add_argument("--exam", choices=("rhcsa", "rhce"), default="rhcsa")
    s.add_argument("--changed", action="store_true", help="only tasks not yet verified in their current form")
    s.add_argument("--sweep", action="store_true",
                   help="parameter sweep: run every task once per value of its choice parameters")
    s.set_defaults(func=cmd_selftest)


def cmd_content_download(args: argparse.Namespace) -> int:
    from . import content

    st = config.load()
    try:
        root = content.download(st, on_line=_printer() if args.verbose else None,
                                on_step=lambda s: print(f"==> {s}", flush=True),
                                with_code_server=st.code_server and not args.no_code_server)
    except content.ContentError as exc:
        return _fail(exc, "Downloading the RHCE content", "rhce")
    print(f"RHCE content ready in {root}")
    return 0


def register_content(sub: argparse._SubParsersAction) -> None:
    c = sub.add_parser("content", help="one-time download of RHCE lab content (needs internet)")
    csub = c.add_subparsers(dest="content_cmd", required=True)
    d = csub.add_parser("download", help="download ansible-navigator, collections, code-server")
    d.add_argument("-v", "--verbose", action="store_true")
    d.add_argument("--no-code-server", action="store_true")
    d.set_defaults(func=cmd_content_download)
