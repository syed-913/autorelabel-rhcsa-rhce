"""Command-line interface. With no arguments the TUI starts; every TUI action
also exists here for scripting (add --json where noted)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__, banner, config, doctor, log, paths

_TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
_SYM = {
    doctor.Status.OK: ("✔", "\x1b[32m"),
    doctor.Status.WARN: ("!", "\x1b[33m"),
    doctor.Status.FAIL: ("✘", "\x1b[31m"),
    doctor.Status.INFO: ("•", "\x1b[36m"),
}


def _c(text: str, code: str) -> str:
    return f"{code}{text}\x1b[0m" if _TTY else text


def print_checks(checks: list[doctor.Check]) -> None:
    for c in checks:
        sym, color = _SYM[c.status]
        print(f" {_c(sym, color)} {c.title:<38} {_c(c.detail, chr(27) + '[2m')}")
        if c.fix and c.status in (doctor.Status.FAIL, doctor.Status.WARN):
            for line in c.fix:
                print(f"      {_c(line, chr(27) + '[2m') if line.startswith('#') else line}")
    blocking = doctor.blocking(checks)
    print()
    if blocking:
        print(_c(f" {len(blocking)} problem(s) must be fixed. Run the commands above, then re-run "
                 "./autorelabel doctor.", "\x1b[1;31m"))
    else:
        print(_c(" Host is ready.", "\x1b[1;32m"))


def cmd_doctor(args: argparse.Namespace) -> int:
    settings = config.load()
    checks = doctor.run(settings, exam=args.exam)
    if args.json:
        print(json.dumps([asdict(c) | {"status": c.status.value} for c in checks], indent=2))
    else:
        print_checks(checks)
    return 1 if doctor.blocking(checks) else 0


def cmd_report(args: argparse.Namespace) -> int:
    from . import report

    log_file = Path(args.log).expanduser() if args.log else None
    path = report.write("Reported by the user", args.message or "something went wrong", log_file=log_file,
                        exam=args.exam or "")
    report.print_notice(path, asked=True)
    return 0


def cmd_banner(_args: argparse.Namespace) -> int:
    sys.stdout.write(banner.render_ansi())
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    settings = config.load()
    if args.set:
        for item in args.set:
            key, _, value = item.partition("=")
            if not hasattr(settings, key):
                print(f"unknown setting: {key}", file=sys.stderr)
                return 2
            current = getattr(settings, key)
            if isinstance(current, bool):
                setattr(settings, key, value.lower() in ("1", "true", "yes", "on"))
            elif isinstance(current, list):
                setattr(settings, key, [int(x) for x in value.split(",") if x])
            else:
                setattr(settings, key, value)
        problems = settings.validate()
        if problems:
            print("; ".join(problems), file=sys.stderr)
            return 2
        config.save(settings)
    print(json.dumps(asdict(settings), indent=2))
    return 0


def _tui(start: str | None = None) -> int:
    from .tui.app import run_tui

    return run_tui(start)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autorelabel",
        description="RHCSA & RHCE practice exam simulator for RHEL 10. Run without arguments for the TUI.",
    )
    p.add_argument("--version", action="version", version=f"autorelabel {__version__}")
    p.add_argument("--debug", action="store_true", help="verbose logging (also VAGRANT_LOG/PACKER_LOG)")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    d = sub.add_parser("doctor", help="check that this host can run the labs")
    d.add_argument("--exam", choices=("rhcsa", "rhce"), default="rhcsa")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_doctor)

    r = sub.add_parser("report", help="write a problem report to post on the issue tracker")
    r.add_argument("message", nargs="?", help="what went wrong, in a few words")
    r.add_argument("--log", help="the log to include (default: the app log)")
    r.add_argument("--exam", choices=("rhcsa", "rhce"))
    r.set_defaults(func=cmd_report)

    b = sub.add_parser("banner", help="print the banner")
    b.set_defaults(func=cmd_banner)

    c = sub.add_parser("config", help="show or change settings (key=value)")
    c.add_argument("set", nargs="*", metavar="key=value")
    c.set_defaults(func=cmd_config)

    sub.add_parser("uninstall", help="remove everything autorelabel created on this host "
                                     "(--dry-run, --keep-box, --yes)")

    for name, hlp in (("rhcsa", "open the TUI and start a new RHCSA exam"),
                      ("rhce", "open the TUI and start a new RHCE exam"),
                      ("resume", "open the TUI and return to the current session")):
        sp = sub.add_parser(name, help=hlp)
        sp.set_defaults(func=lambda a, n=name: _tui(n))

    from . import commands  # registers the remaining subcommands
    commands.register(sub)
    return p


def main(argv: list[str]) -> int:
    paths.ensure_workspace()
    parser = build_parser()
    args = parser.parse_args(argv)
    log.setup(debug=getattr(args, "debug", False))
    if args.command is None:
        return _tui()
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        if args.debug:
            raise
        from .commands import _fail

        log.get().exception("./autorelabel %s failed", " ".join(argv))
        return _fail(exc, f"./autorelabel {' '.join(argv)}", getattr(args, "exam", "") or "")
