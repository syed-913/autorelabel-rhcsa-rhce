"""The console keeper: VirtualBox serial consoles stay drained, and console sessions reach the VM
through it. Fake VMs are Unix socket servers, as VirtualBox's serial ports in server mode are."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from autorelabel import console_keeper as ck
from autorelabel.providers import virtualbox as vb

SRC = Path(__file__).resolve().parents[1] / "src"


class FakeVM:
    """A serial port in server mode: one client at a time, writes block until it reads."""

    def __init__(self, directory: Path, name: str) -> None:
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(ck.vm_socket(directory, name)))
        self.server.listen(1)
        self.server.settimeout(10)
        self.conn: socket.socket | None = None

    def accept(self) -> socket.socket:
        self.conn, _ = self.server.accept()
        self.conn.settimeout(10)
        return self.conn

    def close(self) -> None:
        if self.conn:
            self.conn.close()
        self.server.close()


def _keeper(directory: Path, idle: float = 1.0) -> threading.Thread:
    t = threading.Thread(target=ck.run, args=(directory, idle), daemon=True)
    t.start()
    deadline = time.monotonic() + 5
    while not ck.alive(directory / "keeper.sock"):
        assert time.monotonic() < deadline, "keeper did not start"
        time.sleep(0.02)
    return t


def _attach(directory: Path, name: str) -> tuple[socket.socket, bytes]:
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.settimeout(10)
    c.connect(str(directory / "keeper.sock"))
    c.sendall(f"{name}\n".encode())
    status = b""
    while not status.endswith(b"\n"):
        chunk = c.recv(1)
        if not chunk:
            break
        status += chunk
    return c, status


def _recv_until(s: socket.socket, want: bytes) -> bytes:
    got = b""
    while want not in got:
        chunk = s.recv(4096)
        assert chunk, f"connection closed before {want!r} arrived (got {got!r})"
        got += chunk
    return got


def test_an_unwatched_console_is_drained(tmp_path):
    vm = FakeVM(tmp_path, "node1")
    keeper = _keeper(tmp_path)
    conn = vm.accept()                       # the keeper connects by itself
    conn.sendall(b"x" * (4 << 20))           # a boot's worth of kernel messages: never blocks
    vm.close()
    keeper.join(10)
    assert not keeper.is_alive(), "keeper did not exit once no VM was left"
    assert not (tmp_path / "keeper.sock").exists()


def test_console_sessions_are_relayed(tmp_path):
    vm = FakeVM(tmp_path, "node1")
    _keeper(tmp_path)
    conn = vm.accept()
    client, status = _attach(tmp_path, "node1")
    assert status == b"OK\n"
    conn.sendall(b"node1 login: ")
    assert b"node1 login: " in _recv_until(client, b"login: ")
    client.sendall(b"root\r")
    assert _recv_until(conn, b"\r") == b"root\r"
    conn.close()                             # the VM powers off: the session ends
    assert client.recv(4096) == b""
    client.close()
    vm.close()


def test_attaching_to_a_vm_that_is_off(tmp_path):
    _keeper(tmp_path)
    client, status = _attach(tmp_path, "node9")
    assert status.startswith(b"ERR ")
    client.close()


def test_one_keeper_at_a_time(tmp_path):
    first = _keeper(tmp_path, idle=2)
    assert ck.run(tmp_path, idle=2) == 0     # returns at once: the first one serves
    first.join(10)
    assert not first.is_alive()


def test_ensure_starts_a_detached_keeper(tmp_path, monkeypatch):
    monkeypatch.setattr(vb, "console_dir", lambda: tmp_path)
    monkeypatch.setattr(vb.paths, "LOGS", tmp_path / "logs")
    monkeypatch.setenv("PYTHONPATH", str(SRC))
    vb.ensure_console_keeper()
    vb.ensure_console_keeper()               # already running: nothing more is started
    pid = int((tmp_path / "keeper.lock").read_text())
    try:
        assert ck.alive(tmp_path / "keeper.sock")
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 5
        while (tmp_path / "keeper.sock").exists():
            assert time.monotonic() < deadline, "keeper.sock left behind after SIGTERM"
            time.sleep(0.05)
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@pytest.mark.parametrize("name", ["", "../etc", "a/b"])
def test_bad_vm_names_are_refused(tmp_path, name):
    _keeper(tmp_path)
    client, status = _attach(tmp_path, name)
    assert status.startswith(b"ERR ")
    client.close()


def test_the_console_bridge_attaches_through_the_keeper(tmp_path):
    vm = FakeVM(tmp_path, "node1")
    _keeper(tmp_path)
    conn = vm.accept()
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    bridge = subprocess.Popen([sys.executable, "-m", "autorelabel.console_bridge",
                               str(tmp_path / "keeper.sock"), "node1"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
    bridge.stdin.write(b"root\n")            # not a terminal: Enter is sent as a carriage return
    bridge.stdin.flush()
    assert _recv_until(conn, b"\r") == b"root\r"
    conn.sendall(b"Password: ")
    out = b""
    while b"Password: " not in out:
        chunk = os.read(bridge.stdout.fileno(), 4096)
        assert chunk, f"bridge ended before the VM's output arrived (got {out!r})"
        out += chunk
    conn.close()                             # the VM goes away: the bridge ends
    assert bridge.wait(timeout=10) == 0
    bridge.stdin.close()
    bridge.stdout.close()
    vm.close()


def test_the_console_bridge_explains_a_vm_that_is_off(tmp_path):
    _keeper(tmp_path)
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    res = subprocess.run([sys.executable, "-m", "autorelabel.console_bridge",
                          str(tmp_path / "keeper.sock"), "node2"],
                         stdin=subprocess.DEVNULL, capture_output=True, env=env, timeout=10)
    assert res.returncode == 1
    assert b"node2 is not running" in res.stderr


def test_what_a_vm_says_last_reaches_the_session(tmp_path):
    vm = FakeVM(tmp_path, "node1")
    _keeper(tmp_path)
    conn = vm.accept()
    client, _ = _attach(tmp_path, "node1")
    conn.sendall(b"reboot: Power down\r\n")
    conn.close()                             # output and power-off arrive together
    got = b""
    while chunk := client.recv(4096):
        got += chunk
    assert b"Power down" in got
    client.close()
    vm.close()
