"""Subprocess helpers with timeouts, process-group cleanup and logging.

Every child runs in its own session so cancelling (Ctrl+C, timeout, TUI quit)
reliably stops the whole tree: vagrant -> ruby -> ssh, packer -> qemu, etc.
"""

from __future__ import annotations

import contextlib
import os
import select
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from . import log

_log = log.get("proc")


@dataclass
class Result:
    cmd: list[str]
    rc: int
    out: str
    err: str
    duration: float
    timed_out: bool = False
    cancelled: bool = False

    @property
    def ok(self) -> bool:
        return self.rc == 0 and not self.timed_out and not self.cancelled

    def tail(self, lines: int = 15) -> str:
        text = (self.err or "") + ("\n" if self.err and self.out else "") + (self.out or "")
        return "\n".join(text.strip().splitlines()[-lines:])


class CommandError(RuntimeError):
    def __init__(self, result: Result, hint: str = ""):
        self.result = result
        self.hint = hint
        what = "timed out" if result.timed_out else f"exited with code {result.rc}"
        super().__init__(f"{' '.join(result.cmd[:3])} ... {what}")


def which(name: str) -> str | None:
    return shutil.which(name)


def _kill_group(proc: subprocess.Popen, grace: Sequence[tuple[int, float]]) -> None:
    for sig, wait in grace:
        if proc.poll() is not None:
            return
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, sig)
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return
            time.sleep(0.1)


GRACEFUL = ((signal.SIGINT, 30.0), (signal.SIGTERM, 10.0), (signal.SIGKILL, 5.0))
QUICK = ((signal.SIGTERM, 3.0), (signal.SIGKILL, 2.0))


def run(
    cmd: Sequence[str],
    *,
    timeout: float | None = 60,
    env: Mapping[str, str] | None = None,
    cwd: Path | str | None = None,
    input: str | None = None,
    check: bool = False,
) -> Result:
    """Run a command to completion and capture its output."""
    cmd = [str(c) for c in cmd]
    start = time.monotonic()
    _log.debug("run: %s", " ".join(cmd))
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(env) if env else None,
            cwd=cwd,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        res = Result(cmd, 127, "", f"{cmd[0]}: command not found", 0.0)
        if check:
            raise CommandError(res) from None
        return res
    timed_out = False
    try:
        out, err = proc.communicate(input=input, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(proc, QUICK)
        out, err = proc.communicate()
    res = Result(cmd, proc.returncode, out or "", err or "", time.monotonic() - start, timed_out)
    if not res.ok:
        _log.debug("rc=%s timed_out=%s stderr=%s", res.rc, timed_out, (err or "").strip()[-500:])
    if check and not res.ok:
        raise CommandError(res)
    return res


def stream(
    cmd: Sequence[str],
    *,
    on_line: Callable[[str], None] | None = None,
    timeout: float | None = None,
    env: Mapping[str, str] | None = None,
    cwd: Path | str | None = None,
    log_file: Path | None = None,
    cancel: threading.Event | None = None,
    check: bool = False,
    input: str | None = None,
) -> Result:
    """Run a long command, delivering merged stdout/stderr line by line.

    Cancellation and timeouts stop the whole process group gracefully: SIGINT
    first (vagrant and packer clean up on SIGINT), then SIGTERM, then SIGKILL.
    """
    cmd = [str(c) for c in cmd]
    start = time.monotonic()
    _log.info("stream: %s", " ".join(cmd))
    lines: list[str] = []
    fh = open(log_file, "a", encoding="utf-8") if log_file else None
    try:
        if fh:
            fh.write(f"$ {' '.join(cmd)}\n")
            fh.flush()
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=dict(env) if env else None,
                cwd=cwd,
                text=True,
                bufsize=1,
                start_new_session=True,
                errors="replace",
            )
        except FileNotFoundError:
            res = Result(cmd, 127, "", f"{cmd[0]}: command not found", 0.0)
            if check:
                raise CommandError(res) from None
            return res
        assert proc.stdout is not None
        if input is not None and proc.stdin is not None:
            try:
                proc.stdin.write(input)
                proc.stdin.close()
            except BrokenPipeError:
                pass
        timed_out = cancelled = False
        while True:
            if cancel is not None and cancel.is_set():
                cancelled = True
                break
            if timeout is not None and time.monotonic() - start > timeout:
                timed_out = True
                break
            ready, _, _ = select.select([proc.stdout], [], [], 0.25)
            if ready:
                line = proc.stdout.readline()
                if line == "":
                    break
                line = line.rstrip("\n")
                lines.append(line)
                if len(lines) > 4000:
                    del lines[:2000]
                if fh:
                    fh.write(log.redact(line) + "\n")
                    fh.flush()
                if on_line:
                    on_line(line)
            elif proc.poll() is not None:
                rest = proc.stdout.read()
                for line in rest.splitlines():
                    lines.append(line)
                    if fh:
                        fh.write(log.redact(line) + "\n")
                    if on_line:
                        on_line(line)
                break
        if timed_out or cancelled:
            _kill_group(proc, GRACEFUL)
        proc.wait()
        res = Result(cmd, proc.returncode, "\n".join(lines), "", time.monotonic() - start, timed_out, cancelled)
        if fh:
            fh.write(f"# exit={res.rc} timed_out={timed_out} cancelled={cancelled} {res.duration:.0f}s\n")
        if check and not res.ok:
            raise CommandError(res)
        return res
    finally:
        if fh:
            fh.close()
