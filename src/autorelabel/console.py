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

from .providers import libvirt as lv

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[()][A-Za-z0-9]|\r")
DETACH = b"\x1d"  # Ctrl+]


def interactive_command(domain: str) -> list[str]:
    return lv.console_command(domain)


def probe(domain: str, seconds: float = 4.0) -> str:
    """Attach to the console, press Enter, capture what the console shows, detach."""
    master, slave = pty.openpty()
    try:
        p = subprocess.Popen(lv.console_command(domain), stdin=slave, stdout=slave, stderr=slave,
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
    ("relabel", re.compile(r"relabel", re.I),
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
    for kind, rx, msg in _PATTERNS:
        if rx.search(text):
            return Diagnosis(kind, msg)
    return Diagnosis("unknown", "no recognisable console output.")
