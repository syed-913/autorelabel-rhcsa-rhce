"""Serial console: interactive attach for candidates (GRUB, rd.break) and a
non-interactive probe the grader uses to diagnose nodes that don't come back."""

from __future__ import annotations

import os
import pty
import re
import select
import subprocess
import time
from dataclasses import dataclass
from types import ModuleType

from .providers import libvirt as lv

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()][A-Za-z0-9]|\r")
DETACH = b"\x1d"  # Ctrl+]


def interactive_command(domain: str, hv: ModuleType = lv) -> list[str]:
    return hv.console_command(domain)


def probe(domain: str, hv: ModuleType = lv, seconds: float = 4.0) -> str:
    """Attach to the console, press Enter, capture what the console shows, detach."""
    master, slave = pty.openpty()
    try:
        p = subprocess.Popen(hv.console_command(domain), stdin=slave, stdout=slave, stderr=slave,
                             start_new_session=True, close_fds=True)
    except FileNotFoundError:
        os.close(master)
        os.close(slave)
        return ""
    os.close(slave)
    buf = bytearray()
    try:
        time.sleep(0.8)
        os.write(master, b"\r")
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            r, _, _ = select.select([master], [], [], 0.2)
            if r:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                buf.extend(chunk)
        try:
            os.write(master, DETACH)
        except OSError:
            pass
        time.sleep(0.3)
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        os.close(master)
    return _ANSI.sub("", buf.decode("utf-8", "replace"))


@dataclass(frozen=True)
class Diagnosis:
    kind: str          # emergency | grub | panic | relabel | booting | login | unknown
    message: str

    @property
    def terminal(self) -> bool:
        """True when waiting longer will not help."""
        return self.kind in ("emergency", "grub", "panic")


_PATTERNS = [
    ("relabel", re.compile(r"policy relabel is required|Relabeling could take|Relabeling /", re.I),
     "SELinux is relabelling the file system (normal after a root password reset)."),
    ("emergency", re.compile(r"emergency mode|Give root password for maintenance|Press Enter for maintenance",
                             re.I),
     "booted into emergency mode, most likely a bad /etc/fstab entry or a missing volume."),
    ("grub", re.compile(r"^\s*grub>|grub rescue>|minimal BASH-like line editing", re.I | re.M),
     "stopped at the GRUB prompt: the boot loader configuration is broken."),
    ("panic", re.compile(r"Kernel panic|not syncing", re.I),
     "kernel panic: check kernel arguments (grubby) or the root device."),
    ("login", re.compile(r"login:\s*$", re.I | re.M),
     "booted to a login prompt, but the grader could not log in over SSH."),
    ("booting", re.compile(r"Starting|Started|Reached target|systemd\[1\]", re.I),
     "still booting."),
]


def diagnose(text: str) -> Diagnosis:
    """Judge the *current* screen: only the last part of the captured output counts,
    so messages from earlier in the boot don't mislead the diagnosis."""
    lines = [line for line in text.splitlines() if line.strip()]
    tail = "\n".join(lines[-25:])
    for kind, rx, msg in _PATTERNS:
        if rx.search(tail):
            return Diagnosis(kind, msg)
    return Diagnosis("unknown", "no recognisable console output.")


class ConsoleError(RuntimeError):
    pass


def run_commands(domain: str, root_password: str, text: str, *, timeout: float = 240,
                 hv: ModuleType = lv) -> str:
    """Log in on the serial console (emergency-mode maintenance prompt or a normal login
    prompt) as root and type `text` line by line, like a candidate would. Used by
    self-tests for tasks that leave a node unbootable. Returns the captured output."""
    master, slave = pty.openpty()
    p = subprocess.Popen(hv.console_command(domain), stdin=slave, stdout=slave, stderr=slave,
                         start_new_session=True, close_fds=True)
    os.close(slave)
    buf = bytearray()

    def read_until(patterns: list[str], limit: float) -> str:
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            r, _, _ = select.select([master], [], [], 0.3)
            if r:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    break
                buf.extend(chunk)
                text_now = _ANSI.sub("", buf.decode("utf-8", "replace"))
                for pat in patterns:
                    if re.search(pat, text_now[-600:], re.I | re.M):
                        return pat
        tail = _ANSI.sub("", buf.decode("utf-8", "replace"))[-300:].strip()
        raise ConsoleError(f"console: none of {patterns} seen within {limit:.0f}s; last output: {tail!r}")

    def send(s: str) -> None:
        os.write(master, s.encode())

    try:
        time.sleep(1.0)
        send("\r")
        hit = read_until([r"Give root password", r"Press Enter for maintenance", r"login:\s*$",
                          r"#\s*$"], timeout / 2)
        if hit.startswith("Give root") or hit.startswith("Press Enter"):
            send(root_password + "\r")
            read_until([r"#\s*$"], 30)
        elif hit.startswith("login"):
            send("root\r")
            read_until([r"[Pp]assword:\s*$"], 20)
            send(root_password + "\r")
            read_until([r"#\s*$"], 30)
        for line in text.splitlines():
            send(line + "\r")
            time.sleep(0.15)
        # A candidate reboots (or continues the boot) afterwards, which writes everything to disk;
        # a node left in emergency mode gets hard-reset by the grader, so sync first.
        send("sync; echo __AR_DONE__$((40+2))\r")
        read_until([r"__AR_DONE__42"], timeout / 2)
        return _ANSI.sub("", buf.decode("utf-8", "replace"))
    finally:
        try:
            os.write(master, DETACH)
        except OSError:
            pass
        time.sleep(0.3)
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
        os.close(master)
