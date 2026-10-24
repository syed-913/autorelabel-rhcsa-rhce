"""Problem reports. When something fails that the user can't be expected to fix (a tool on the
host changed, a VM didn't come up, a bug), the app writes a report with what's needed to
diagnose it, and asks the user to post it on the project's issue tracker.

Reports go to .workspace/reports/ (removed by uninstall). Before anything is written, the home
directory, user name and host name are replaced and secrets are masked; the user reads the
report before posting it anyway.
"""

from __future__ import annotations

import getpass
import platform
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

from . import __version__, log, paths

REPO_URL = "https://github.com/syed-913/autorelabel-rhcsa-rhce"
ISSUES_URL = f"{REPO_URL}/issues/new?template=problem-report.yml"
LOG_LINES = 80
DOCTOR_TIMEOUT = 45


def reportable(exc: BaseException) -> bool:
    """Everything except interruptions and errors marked as the user's to fix (`user_fixable`:
    the exam is locked, another instance holds the lab, VirtualBox Manager is open...)."""
    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
        return False
    return not getattr(exc, "user_fixable", False)


def describe(exc: BaseException) -> str:
    """The error message; for an exception that isn't one of autorelabel's own (a bug), with its type."""
    text = str(exc)
    if type(exc).__module__.split(".")[0] != "autorelabel":
        return f"{type(exc).__name__}: {text}" if text else type(exc).__name__
    return text or type(exc).__name__


def sanitize(text: str) -> str:
    text = log.redact(text)
    text = text.replace(str(Path.home()), "~")
    for name, placeholder in ((getpass.getuser(), "<user>"), (socket.gethostname(), "<host>")):
        if name and len(name) >= 3:
            text = re.sub(rf"(?<![\w.-]){re.escape(name)}(?![\w-])", placeholder, text)
    return text


def _git_version() -> str:
    try:
        rev = subprocess.run(["git", "-C", str(paths.ROOT), "describe", "--tags", "--always", "--dirty"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return rev.stdout.strip() if rev.returncode == 0 else ""


def _os_release() -> str:
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip('"')
    except OSError:
        pass
    return platform.system()


def _doctor(exam: str) -> list[str]:
    """The doctor's checks (tool versions, plugins, memory, storage...), with a time limit:
    a VirtualBox service busy with another profile must not hold the report up."""
    from . import config, doctor

    out: list[str] = []

    def run() -> None:
        sym = {doctor.Status.OK: "ok", doctor.Status.WARN: "WARN", doctor.Status.FAIL: "FAIL",
               doctor.Status.INFO: "info"}
        for c in doctor.run(config.load(), exam=exam):
            out.append(f"- {sym[c.status]}: {c.title}: {c.detail}")

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(DOCTOR_TIMEOUT)
    return out if not t.is_alive() else out + [f"- (the doctor did not finish within {DOCTOR_TIMEOUT} s)"]


def _tail(path: Path, lines: int = LOG_LINES) -> str:
    try:
        return "\n".join(path.read_text(errors="replace").splitlines()[-lines:])
    except OSError as exc:
        return f"(could not read the log: {exc})"


def render(what: str, message: str, *, hint: str = "", log_file: Path | None = None,
           exc: BaseException | None = None, exam: str = "") -> str:
    from . import config

    st = config.load()
    lines = [
        f"### What failed\n\n{what}: {message}",
        *([f"\nHint shown: {hint}"] if hint else []),
        "\n### Environment\n",
        f"- autorelabel {__version__} ({_git_version() or 'not a git checkout'})",
        f"- host: {_os_release()}, kernel {platform.release()}, Python {platform.python_version()}",
        f"- provider: {st.provider or 'not chosen'}, profile {st.profile}" + (f", exam {exam}" if exam else ""),
        "\n### Doctor\n",
        *_doctor(exam or "rhcsa"),
    ]
    if exc is not None and not isinstance(exc, (KeyboardInterrupt, SystemExit)):
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()
        lines += ["\n### Traceback\n", "```text", tb, "```"]
    app_log = paths.LOGS / "autorelabel.log"
    if log_file is None:   # no failing operation: the most recent one, then the app log
        ops = sorted((f for f in paths.LOGS.glob("*.log") if f != app_log), key=lambda f: f.stat().st_mtime)
        log_file = ops[-1] if ops else None
    logs = [(log_file, LOG_LINES)] + ([(app_log, 30)] if log_file != app_log else [])
    for f, n in logs:
        if f is not None and f.exists():
            lines += [f"\n### Log: {f.name} (last {n} lines)\n", "```text", _tail(f, n), "```"]
    return sanitize("\n".join(lines)) + "\n"


def write(what: str, message: str, *, hint: str = "", log_file: Path | None = None,
          exc: BaseException | None = None, exam: str = "") -> Path:
    """Write a problem report and return its path. Never raises: a broken report must not hide
    the original error."""
    reports = paths.WORKSPACE / "reports"
    slug = re.sub(r"[^a-z0-9]+", "-", message.lower()).strip("-")[:48] or "problem"
    path = reports / f"{time.strftime('%Y%m%d-%H%M%S')}-{slug}.md"
    try:
        body = render(what, message, hint=hint, log_file=log_file, exc=exc, exam=exam)
    except Exception as e:  # still write what we know
        body = sanitize(f"### What failed\n\n{what}: {message}\n\n(report incomplete: {e!r})\n")
    try:
        reports.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    except OSError:
        pass
    log.get("report").error("problem report %s: %s: %s", path, what, message)
    return path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return sanitize(str(path))


def notice(path: Path, has_hint: bool = False, asked: bool = False) -> str:
    """What to tell the user once a report is written (plain text, for the CLI and the TUI)."""
    first = ("To report it" if asked else "If the hint above doesn't solve it, please report it" if has_hint
             else "This looks like a problem autorelabel can't solve on its own. Please report it")
    return (f"{first}, so it can be fixed for everyone:\n"
            f"  1. open {ISSUES_URL}\n"
            f"  2. paste the problem report ({display_path(path)}) and say what you were doing.\n"
            "The report holds your OS and tool versions and the end of the log, with your home\n"
            "directory, user name and host name replaced. Read it before you post it.")


def print_notice(path: Path, has_hint: bool = False, asked: bool = False) -> None:
    print(f"\nProblem report: {display_path(path)}", file=sys.stderr)
    print(notice(path, has_hint, asked), file=sys.stderr)
