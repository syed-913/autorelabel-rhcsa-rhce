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

    def line(s: str) -> None:
        if args.verbose:
            print(f"    {s}", flush=True)

    try:
        log_file = box.build(settings, provider, on_line=line, on_step=step)
    except box.BoxError as exc:
        print(f"log: {exc.log_file}", file=sys.stderr)
        return _err(str(exc), exc.hint)
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
    if args.write:
        out = paths.ROOT / "docs" / f"COVERAGE-{args.exam.upper()}.md"
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}")
    elif args.check:
        out = paths.ROOT / "docs" / f"COVERAGE-{args.exam.upper()}.md"
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            return _err(f"{out.name} is stale", f"run ./autorelabel bank coverage {args.exam} --write")
        print(f"{out.name} is up to date")
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

    lab = _lab(args.exam)
    pw = {n: secrets_util.password() for n in lab.names()}
    try:
        log_file = lab.up(root_passwords=pw, on_step=lambda s: print(f"==> {s}", flush=True),
                          on_line=(lambda s: print(f"    {s}", flush=True)) if args.verbose else None)
    except LabError as exc:
        print(f"log: {exc.log_file}", file=sys.stderr)
        return _err(str(exc), exc.hint)
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
    _lab(args.exam).destroy(on_line=lambda s: print(f"    {s}", flush=True))
    print("Lab destroyed (networks, pool and box are kept; use uninstall to remove everything).")
    return 0


def register(sub: argparse._SubParsersAction) -> None:
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
