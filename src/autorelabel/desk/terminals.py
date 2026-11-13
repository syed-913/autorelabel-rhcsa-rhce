"""The Exam Desk's shells: one PTY per terminal, owned by the desk process.

A terminal outlives the browser tab that shows it: closing or reloading the tab, or opening the
desk in a second window, reattaches to the same shell. Each terminal keeps the tail of its output
(SCROLLBACK) to replay on reattach. In full-screen programs (vim, less, nmtui: the "alternate
screen") a replay would draw garbage, so the terminal is resized by one column and back and the
program repaints itself.

Flow control: every client acknowledges the bytes it has drawn. When a client is more than
HIGH_WATER behind, the desk stops reading the PTY until it is under LOW_WATER again, so `find /`
or a journal without a pager can't freeze the tab or grow this process's memory.

When the exam is locked (time is up) or grading, input is dropped here, not in the browser: the
page can show "read-only", but this is what enforces it.
"""

from __future__ import annotations

import asyncio
import fcntl
import os
import re
import signal
import struct
import subprocess
import sys
import termios
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PTY_EXEC = Path(__file__).with_name("pty_exec.py")
SCROLLBACK = 1 << 20
HIGH_WATER = 512 * 1024
LOW_WATER = 128 * 1024
READ_SIZE = 64 * 1024
ALT_ON = re.compile(rb"\x1b\[\?(?:1049|1047|47)h")
ALT_OFF = re.compile(rb"\x1b\[\?(?:1049|1047|47)l")


@dataclass
class Client:
    send: Callable[[bytes], Any]             # queues bytes for one browser tab
    unacked: int = 0


@dataclass
class Terminal:
    id: str
    node: str
    kind: str                                 # ssh | console | (tests) sh
    argv: list[str]
    title: str = ""
    cols: int = 100
    rows: int = 30
    fd: int = -1
    proc: subprocess.Popen | None = None
    scrollback: bytearray = field(default_factory=bytearray)
    alt_screen: bool = False
    exited: bool = False
    clients: list[Client] = field(default_factory=list)
    paused: bool = False
    loop: asyncio.AbstractEventLoop | None = None
    read_only: Callable[[], bool] = lambda: False

    # --- life cycle --------------------------------------------------------------------------------
    def start(self, loop: asyncio.AbstractEventLoop, env: dict[str, str] | None = None) -> None:
        master, slave = os.openpty()
        self.fd = master
        self.loop = loop
        self._set_size(self.cols, self.rows)
        os.set_blocking(master, False)
        child_env = {**(env or os.environ), "TERM": "xterm-256color", "COLORTERM": "truecolor"}
        self.proc = subprocess.Popen(
            [sys.executable, str(PTY_EXEC), *self.argv],          # by path: works from any folder
            stdin=slave, stdout=slave, stderr=slave, close_fds=True, start_new_session=True, env=child_env)
        os.close(slave)
        loop.add_reader(master, self._readable)

    def close(self) -> None:
        if self.loop and self.fd >= 0 and not self.exited:
            self.loop.remove_reader(self.fd)
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
        if self.fd >= 0:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = -1
        self.exited = True

    # --- output --------------------------------------------------------------------------------
    def _readable(self) -> None:
        try:
            data = os.read(self.fd, READ_SIZE)
        except BlockingIOError:
            return
        except OSError:                       # EIO: the program ended and the PTY closed
            data = b""
        if not data:
            self._ended()
            return
        self._keep(data)
        for c in list(self.clients):
            c.unacked += len(data)
            c.send(data)
        if any(c.unacked > HIGH_WATER for c in self.clients):
            self.paused = True
            assert self.loop is not None
            self.loop.remove_reader(self.fd)

    def _keep(self, data: bytes) -> None:
        on, off = [m.end() for m in ALT_ON.finditer(data)], [m.end() for m in ALT_OFF.finditer(data)]
        if on or off:
            self.alt_screen = max(on, default=-1) > max(off, default=-1)
        self.scrollback += data
        if len(self.scrollback) > SCROLLBACK:
            del self.scrollback[:len(self.scrollback) - SCROLLBACK]

    def _ended(self) -> None:
        if self.exited:
            return
        assert self.loop is not None
        self.loop.remove_reader(self.fd)
        self.exited = True
        code = self.proc.wait() if self.proc else 0
        note = (f"\r\n\x1b[2m[{self.title or self.kind} ended (exit {code}). "
                "Open a new shell from the node's tab.]\x1b[0m\r\n")
        self._keep(note.encode())
        for c in list(self.clients):
            c.send(note.encode())

    def ack(self, client: Client, count: int) -> None:
        client.unacked = max(0, client.unacked - max(0, count))
        self._maybe_resume()

    def _maybe_resume(self) -> None:
        if self.paused and not self.exited and all(c.unacked <= LOW_WATER for c in self.clients):
            self.paused = False
            assert self.loop is not None
            self.loop.add_reader(self.fd, self._readable)

    # --- clients -------------------------------------------------------------------------------
    def attach(self, send: Callable[[bytes], Any]) -> Client:
        """A new tab: replay the tail of the output, or let a full-screen program repaint."""
        client = Client(send)
        self.clients.append(client)
        if self.alt_screen and not self.exited:
            send(b"\x1b[?1049h\x1b[H\x1b[2J")
            self._nudge()
        else:
            tail = bytes(self.scrollback[-(256 * 1024):])
            cut = tail.find(b"\n") + 1 if len(self.scrollback) > len(tail) else 0
            if tail[cut:]:
                send(tail[cut:])
        return client

    def detach(self, client: Client) -> None:
        if client in self.clients:
            self.clients.remove(client)
        self._maybe_resume()

    # --- input and size ------------------------------------------------------------------------
    def write(self, data: bytes) -> bool:
        """Typed input. False (and nothing written) when the exam is read-only or the shell ended."""
        if self.exited or self.fd < 0 or self.read_only():
            return False
        view = memoryview(data)
        while view:
            try:
                n = os.write(self.fd, view)
            except BlockingIOError:
                continue                       # the PTY's input buffer is full for a moment
            except OSError:
                return False
            view = view[n:]
        return True

    def resize(self, cols: int, rows: int) -> None:
        cols, rows = max(2, min(int(cols), 500)), max(2, min(int(rows), 300))
        if (cols, rows) != (self.cols, self.rows) and self.fd >= 0:
            self.cols, self.rows = cols, rows
            self._set_size(cols, rows)

    def _set_size(self, cols: int, rows: int) -> None:
        try:
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except OSError:
            pass

    def _nudge(self) -> None:
        """Make a full-screen program redraw: one column narrower, then back (two SIGWINCH)."""
        if self.fd < 0 or not self.loop:
            return
        self._set_size(max(2, self.cols - 1), self.rows)
        self.loop.call_later(0.05, self._set_size, self.cols, self.rows)

    def describe(self) -> dict[str, Any]:
        return {"id": self.id, "node": self.node, "kind": self.kind, "title": self.title, "exited": self.exited}
