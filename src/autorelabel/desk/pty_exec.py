"""Run a command with the PTY on its standard input as its controlling terminal.

    python -m autorelabel.desk.pty_exec <command> [args...]

The Exam Desk starts every shell in a new session (`start_new_session=True`), which leaves it with
no controlling terminal; ssh reads the password from /dev/tty and needs one. Opening the terminal
by name in a session that has none makes it the controlling terminal on Linux. Doing that here,
in a fresh process, avoids a pre-exec hook in the desk's own multi-threaded process.
"""

from __future__ import annotations

import os
import sys


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: pty_exec <command> [args...]", file=sys.stderr)
        return 2
    os.close(os.open(os.ttyname(0), os.O_RDWR))      # becomes the controlling terminal
    try:
        os.execvp(argv[0], argv)
    except OSError as exc:
        print(f"could not start {argv[0]}: {exc.strerror}", file=sys.stderr)
        return 127
    return 0                                        # not reached


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
