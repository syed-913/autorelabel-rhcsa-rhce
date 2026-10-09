"""Attach the terminal to a VirtualBox serial port (a Unix socket), like
`virsh console`: raw terminal, Ctrl+] to leave."""

from __future__ import annotations

import os
import select
import socket
import sys
import termios
import tty

DETACH = b"\x1d"


def main(path: str) -> int:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(path)
    except OSError as exc:
        print(f"cannot connect to the serial console ({exc}). Is the VM running?", file=sys.stderr)
        return 1
    stdin = sys.stdin.fileno()
    interactive = os.isatty(stdin)
    old = termios.tcgetattr(stdin) if interactive else None
    try:
        if interactive:
            tty.setraw(stdin)
        while True:
            r, _, _ = select.select([stdin, sock], [], [])
            if stdin in r:
                data = os.read(stdin, 1024)
                if not data or DETACH in data:
                    data = data.split(DETACH, 1)[0]
                    if data:
                        sock.sendall(data)
                    break
                sock.sendall(data.replace(b"\n", b"\r") if not interactive else data)
            if sock in r:
                data = sock.recv(65536)
                if not data:
                    break
                os.write(sys.stdout.fileno(), data)
    finally:
        if old is not None:
            termios.tcsetattr(stdin, termios.TCSADRAIN, old)
        sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
