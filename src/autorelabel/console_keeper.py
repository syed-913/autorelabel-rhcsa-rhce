"""Keeps the serial consoles of VirtualBox lab VMs drained.

A VirtualBox serial port in server mode (a Unix socket) holds back what the guest writes until a
client reads it, and the guest kernel waits on every character of its console messages
(console=ttyS0): with nobody attached, a VM boots at a crawl and SSH never comes up. libvirt's
pty consoles discard output instead. The keeper stays connected to the console of every running
lab VM, discards what nobody watches, and relays console sessions (`autorelabel console`, the
grader's probes) to the VM.

One keeper per user (keeper.lock, which holds its pid); it exits after IDLE seconds with no VM.
Protocol on keeper.sock: the client sends the VM name and a newline; the keeper answers "OK"
and relays bytes both ways, or "ERR <reason>" and closes.
"""

from __future__ import annotations

import fcntl
import os
import select
import signal
import socket
import sys
import time
from pathlib import Path

IDLE = 900            # seconds without a VM console before the keeper exits
SCAN = 0.5            # how often to look for consoles of VMs that just started
CLIENT_BUFFER = 1 << 20
PREFIX, SUFFIX = "console-", ".sock"


def vm_socket(directory: Path, name: str) -> Path:
    return directory / f"{PREFIX}{name}{SUFFIX}"


def _connect(path: Path) -> socket.socket | None:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(str(path))
    except OSError:          # a stale socket of a VM that is off
        s.close()
        return None
    s.settimeout(2)          # input to a guest that doesn't read is dropped, not waited on
    return s


def alive(path: Path) -> bool:
    """Is a keeper listening on this socket?"""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(str(path))
        return True
    except OSError:
        return False
    finally:
        s.close()


class Keeper:
    def __init__(self, directory: Path, idle: float = IDLE) -> None:
        self.dir = directory
        self.idle = idle
        self.vms: dict[str, socket.socket] = {}
        self.clients: dict[socket.socket, str] = {}
        self.out: dict[socket.socket, bytearray] = {}
        self.pending: dict[socket.socket, bytearray] = {}

    def _attach_vm(self, name: str) -> bool:
        if name not in self.vms:
            s = _connect(vm_socket(self.dir, name))
            if s is None:
                return False
            self.vms[name] = s
        return True

    def _scan(self) -> None:
        for p in self.dir.glob(f"{PREFIX}*{SUFFIX}"):
            self._attach_vm(p.name[len(PREFIX):-len(SUFFIX)])

    def _drop_client(self, c: socket.socket) -> None:
        self.clients.pop(c, None)
        self.out.pop(c, None)
        self.pending.pop(c, None)
        c.close()

    def _drop_vm(self, name: str) -> None:
        self.vms.pop(name).close()
        for c in [c for c, n in self.clients.items() if n == name]:
            if c in self.out:
                self._flush(c)       # what the VM said last
            self._drop_client(c)

    def _header(self, c: socket.socket) -> None:
        try:
            data = c.recv(256)
        except OSError:
            data = b""
        buf = self.pending[c]
        buf.extend(data)
        if b"\n" not in buf:
            if not data or len(buf) > 200:
                self._drop_client(c)
            return
        line, rest = bytes(buf).split(b"\n", 1)
        del self.pending[c]
        name = line.decode(errors="replace").strip()
        error = ("no such VM" if not name or "/" in name
                 else None if self._attach_vm(name) else f"{name} is not running")
        if error:
            c.sendall(f"ERR {error}\n".encode())
            c.close()
            return
        c.sendall(b"OK\n")
        c.setblocking(False)
        self.clients[c] = name
        self.out[c] = bytearray()
        if rest:
            self._to_vm(name, rest)

    def _to_vm(self, name: str, data: bytes) -> None:
        try:
            self.vms[name].sendall(data)
        except OSError:
            pass

    def _from_vm(self, name: str) -> None:
        try:
            data = self.vms[name].recv(65536)
        except OSError:
            data = b""
        if not data:          # the VM was powered off
            self._drop_vm(name)
            return
        for c in [c for c, n in self.clients.items() if n == name]:
            buf = self.out[c]
            buf.extend(data)
            del buf[:-CLIENT_BUFFER]
            self._flush(c)

    def _flush(self, c: socket.socket) -> None:
        try:
            sent = c.send(self.out[c])
        except BlockingIOError:
            return
        except OSError:
            self._drop_client(c)
            return
        del self.out[c][:sent]

    def serve(self, listener: socket.socket) -> None:
        last_scan = 0.0
        active = time.monotonic()
        while True:
            now = time.monotonic()
            if now - last_scan >= SCAN:
                self._scan()
                last_scan = now
            if self.vms or self.pending:
                active = now
            elif now - active > self.idle:
                return
            vm_names = {s: n for n, s in self.vms.items()}
            readers = [listener, *vm_names, *self.clients, *self.pending]
            writers = [c for c, b in self.out.items() if b]
            r, w, _ = select.select(readers, writers, [], SCAN)
            for s in r:
                if s is listener:
                    c, _ = listener.accept()
                    self.pending[c] = bytearray()
                elif s in self.pending:
                    self._header(s)
                elif s in self.clients:
                    try:
                        data = s.recv(65536)
                    except OSError:
                        data = b""
                    if data:
                        self._to_vm(self.clients[s], data)
                    else:
                        self._drop_client(s)
                elif s in vm_names and self.vms.get(vm_names[s]) is s:
                    self._from_vm(vm_names[s])
            for c in w:
                if c in self.out:
                    self._flush(c)


def run(directory: Path, idle: float = IDLE) -> int:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / "keeper.sock"
    lock = open(directory / "keeper.lock", "a+")
    deadline = time.monotonic() + 3
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            # Another keeper serves these consoles, or is exiting and about to let go.
            if alive(path) or time.monotonic() > deadline:
                lock.close()
                return 0
            time.sleep(0.1)
    lock.truncate(0)
    lock.write(f"{os.getpid()}\n")
    lock.flush()
    path.unlink(missing_ok=True)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    listener.listen(16)
    try:
        Keeper(directory, idle).serve(listener)
    finally:
        path.unlink(missing_ok=True)
        listener.close()
        lock.truncate(0)
        lock.close()
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))   # clean up keeper.sock when stopped
    sys.exit(run(Path(sys.argv[1])))
