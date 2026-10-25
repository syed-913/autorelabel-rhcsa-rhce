"""Subprocess helpers with timeouts, process-group cleanup and logging.

Every child runs in its own session so cancelling (Ctrl+C, timeout, TUI quit)
reliably stops the whole tree: vagrant -> ruby -> ssh, packer -> qemu, etc.
"""

from __future__ import annotations

import codecs
import contextlib
import os
import re
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


class Progress(str):
    """A line that redraws the one before it (a progress counter such as "Progress: 94%").

    `stream` passes these to `on_line` like any line; the TUI shows them in a progress bar and
    the CLI redraws one terminal line. Only the last value reaches the log and `Result.out`.
    """


_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()][A-Za-z0-9]")
_BREAK = re.compile(r"\r\n|\n|\r")


class _Lines:
    """Splits a child's output into lines the way a terminal shows them: text ended by a bare
    carriage return is drawn over by what follows, so it is a Progress update, not a line."""

    def __init__(self, emit: Callable[[str], None], keep: Callable[[str], None]):
        self.emit, self.keep = emit, keep      # emit: to on_line; keep: to the log and Result.out
        self.buf = ""
        self.shown = ""                        # the progress line being redrawn, "" if none
        self.redrawing = False                 # buf follows a bare carriage return

    def feed(self, text: str, *, final: bool = False, idle: bool = False) -> None:
        """`idle`: no output for a moment. A trailing "\r" is then not waiting for its "\n",
        and a value being redrawn is shown before its terminator (vagrant writes "\r" first)."""
        self.buf += text
        start = 0
        for m in _BREAK.finditer(self.buf):
            if m.group() == "\r" and m.end() == len(self.buf) and not (final or idle):
                break                          # may be the first half of "\r\n"
            self._line(_ANSI.sub("", self.buf[start:m.start()]), redraw=m.group() == "\r")
            self.redrawing = m.group() == "\r"
            start = m.end()
        self.buf = self.buf[start:]
        rest = _ANSI.sub("", self.buf)
        if final:
            if rest:
                self._line(rest, redraw=False)
            self.buf = ""
            self._settle()
        elif idle and self.redrawing and rest.strip() and rest != self.shown:
            self.shown = rest
            self.emit(Progress(rest))

    def _line(self, text: str, redraw: bool) -> None:
        if redraw:
            if text.strip() and text != self.shown:
                self.shown = text
                self.emit(Progress(text))
            return
        if text != self.shown:
            self._settle()
        self.shown = ""
        self.keep(text)
        self.emit(text)

    def _settle(self) -> None:
        """The progress line was drawn over: keep its last value."""
        if self.shown:
            self.keep(self.shown)
            self.shown = ""


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
    """Run a long command, delivering merged stdout/stderr line by line (progress counters
    that redraw their line arrive as Progress updates).

    Cancellation and timeouts stop the whole process group gracefully: SIGINT
    first (vagrant and packer clean up on SIGINT), then SIGTERM, then SIGKILL.
    """
    cmd = [str(c) for c in cmd]
    start = time.monotonic()
    _log.info("stream: %s", " ".join(cmd))
    lines: list[str] = []
    fh = open(log_file, "a", encoding="utf-8") if log_file else None

    def keep(line: str) -> None:
        lines.append(line)
        if len(lines) > 4000:
            del lines[:2000]
        if fh:
            fh.write(log.redact(line) + "\n")
            fh.flush()

    out = _Lines(on_line or (lambda _s: None), keep)
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
                start_new_session=True,
            )
        except FileNotFoundError:
            res = Result(cmd, 127, "", f"{cmd[0]}: command not found", 0.0)
            if check:
                raise CommandError(res) from None
            return res
        assert proc.stdout is not None
        if input is not None and proc.stdin is not None:
            try:
                proc.stdin.write(input.encode())
                proc.stdin.close()
            except BrokenPipeError:
                pass
        fd = proc.stdout.fileno()
        decode = codecs.getincrementaldecoder("utf-8")(errors="replace").decode
        timed_out = cancelled = False
        while True:
            if cancel is not None and cancel.is_set():
                cancelled = True
                break
            if timeout is not None and time.monotonic() - start > timeout:
                timed_out = True
                break
            ready, _, _ = select.select([fd], [], [], 0.25)
            if ready:
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                out.feed(decode(chunk))
            elif proc.poll() is None:
                out.feed("", idle=True)
            else:
                # What is left, without waiting on a pipe a background grandchild keeps open.
                while select.select([fd], [], [], 0)[0] and (chunk := os.read(fd, 65536)):
                    out.feed(decode(chunk))
                break
        out.feed(decode(b"", final=True), final=True)
        if timed_out or cancelled:
            _kill_group(proc, GRACEFUL)
        proc.wait()
        proc.stdout.close()
        res = Result(cmd, proc.returncode, "\n".join(lines), "", time.monotonic() - start, timed_out, cancelled)
        if fh:
            fh.write(f"# exit={res.rc} timed_out={timed_out} cancelled={cancelled} {res.duration:.0f}s\n")
        if check and not res.ok:
            raise CommandError(res)
        return res
    finally:
        if fh:
            fh.close()
