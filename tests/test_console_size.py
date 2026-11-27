"""The console size hook the engine installs on lab nodes (engine.CONSOLE_HOOK_SH).

A serial console can't pass the window's size to the guest, so a login there asks the terminal.
These tests run the hook in bash on a pseudo-terminal, with the test playing the terminal: the
hook only acts on /dev/ttyS*, so the copy under test matches this test's /dev/pts/* instead.
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
import time

import pytest

from autorelabel.engine import CONSOLE_HOOK_SH

QUERY = b"\x1b[6n"


@pytest.fixture()
def hook(tmp_path):
    path = tmp_path / "console.sh"
    path.write_text(CONSOLE_HOOK_SH.replace("/dev/ttyS*)", "/dev/pts/*)"))
    return path


def login(hook, answer: bytes | None, typed_first: bytes = b"") -> tuple[str, float]:
    """Source the hook on a terminal, then print the size the terminal ended up with."""
    pid, fd = pty.fork()
    if pid == 0:                                   # the child: the login shell on the "console"
        os.execvp("bash", ["bash", "--norc", "--noprofile", "-c",
                           f". {hook}; echo SIZE=$(stty size) LEFT=${{__ar_rows-none}}"])
    if typed_first:
        os.write(fd, typed_first)
    out, start, answered = b"", time.monotonic(), False
    while True:
        ready, _, _ = select.select([fd], [], [], 5)
        if not ready:
            break
        try:
            chunk = os.read(fd, 4096)
        except OSError:                            # EIO: the shell ended
            break
        if not chunk:
            break
        out += chunk
        if QUERY in out and not answered and answer is not None:
            answered = True
            os.write(fd, answer)
    os.waitpid(pid, 0)
    return out.decode(errors="replace"), time.monotonic() - start


def test_a_console_login_takes_the_size_the_terminal_reports(hook):
    out, _ = login(hook, b"\x1b[45;132R")
    assert "SIZE=45 132" in out
    assert "LEFT=none" in out                      # no variables left behind in the shell


def test_a_key_pressed_before_the_answer_does_not_spoil_it(hook):
    out, _ = login(hook, b"\x1b[40;120R", typed_first=b"\r")
    assert "SIZE=40 120" in out


def test_a_terminal_that_never_answers_costs_a_second_and_changes_nothing(hook):
    out, took = login(hook, None)
    assert "SIZE=0 0" in out
    assert took < 3


@pytest.mark.parametrize("pattern", ["real", "test"])
def test_it_does_nothing_without_a_terminal(hook, tmp_path, pattern):
    """The grader, scripts and SSH commands source profile.d with no terminal: no output at all."""
    path = tmp_path / "real.sh"
    path.write_text(CONSOLE_HOOK_SH)
    target = path if pattern == "real" else hook
    res = subprocess.run(["bash", "-c", f". {target}; echo done"], stdin=subprocess.DEVNULL,
                         capture_output=True, timeout=10)
    assert res.stdout == b"done\n" and res.stderr == b""
