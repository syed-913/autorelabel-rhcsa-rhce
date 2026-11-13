"""Checks shared by autorelabel's servers on 127.0.0.1 (the results dashboard, and later the Exam
Desk). "Only on this computer" is not a boundary by itself: any web page can make the browser
send requests to 127.0.0.1, a public name can be made to resolve to it (DNS rebinding), and
other users of this computer can connect to the port. The callers check the Host header for
the first, and this module answers the third: which user owns the other end of a connection.
"""

from __future__ import annotations

import os
import socket
import struct
from pathlib import Path

PROC_TCP = Path("/proc/net/tcp")


def _proc_address(address: tuple[str, int]) -> str:
    """('127.0.0.1', 8080) as /proc/net/tcp writes it: the address as the kernel's native u32 in
    hex, then the port in hex ('0100007F:1F90' on x86)."""
    ip, port = address[0], address[1]
    return f"{struct.unpack('=I', socket.inet_aton(ip))[0]:08X}:{port:04X}"


def peer_uid(conn: socket.socket, table: Path = PROC_TCP) -> int | None:
    """The uid that owns the client end of a loopback TCP connection, or None if it can't be
    found. The client's socket is the line whose local address is our peer and whose remote
    address is us."""
    try:
        peer, own = _proc_address(conn.getpeername()), _proc_address(conn.getsockname())
        lines = table.read_text().splitlines()[1:]
    except (OSError, ValueError):
        return None
    for line in lines:
        fields = line.split()
        if len(fields) > 7 and fields[1] == peer and fields[2] == own:
            try:
                return int(fields[7])
            except ValueError:
                return None
    return None


def same_user(conn: socket.socket, table: Path = PROC_TCP) -> bool:
    """True when the program at the other end runs as this user. Unknown counts as no."""
    return peer_uid(conn, table) == os.getuid()


def host_ok(host_header: str, port: int) -> bool:
    """The Host header names this server as 127.0.0.1 or localhost with its own port; anything
    else is a page that reached us under another name (DNS rebinding)."""
    return host_header in (f"127.0.0.1:{port}", f"localhost:{port}")
