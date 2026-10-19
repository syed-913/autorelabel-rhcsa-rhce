"""Run scripts on lab VMs over the management network (the grader channel).

Uses the per-VM key Vagrant generated, the `vagrant` user and sudo. Connection
multiplexing keeps dozens of checks fast. Nothing is left on the guest: scripts
are streamed over stdin and run with `sudo -n bash -s`.
"""

from __future__ import annotations

import os
import shlex
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from . import proc

SSH_OPTS = [
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
    "-o", "IdentitiesOnly=yes",
    "-o", "ConnectTimeout=10",
    "-o", "ServerAliveInterval=5",
    "-o", "ServerAliveCountMax=3",
    "-o", "ControlMaster=auto",
    "-o", "ControlPersist=60",
]


def _control_dir() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    d = Path(runtime) / "autorelabel" if runtime else Path(f"/tmp/autorelabel-{os.getuid()}")
    d.mkdir(mode=0o700, parents=True, exist_ok=True)
    return d


@dataclass(frozen=True)
class Target:
    name: str
    host: str
    key: Path
    user: str = "vagrant"
    port: int = 22

    def control_path(self) -> str:
        # Unix sockets are limited to ~108 bytes, so keep this short and independent of
        # where the repository lives: /run/user/<uid>/autorelabel/<hash>.
        return str(_control_dir() / "%C")


def ssh_base(t: Target) -> list[str]:
    return ["ssh", *SSH_OPTS, "-o", f"ControlPath={t.control_path()}", "-i", str(t.key),
            "-p", str(t.port), f"{t.user}@{t.host}"]


def _wrap(script: str, env: dict[str, str] | None) -> str:
    """The script reaches `bash -s` on stdin. Wrapped in one { } group it is parsed completely
    before it runs, so it can give its commands /dev/null as stdin: nothing in it (ssh, cat,
    a stray read) can swallow the rest of the script."""
    prelude = "".join(f"export {k}={shlex.quote(str(v))}\n" for k, v in (env or {}).items())
    # Behave like a root login shell, not like sudo: root's usual PATH (sudo's secure_path drops
    # /usr/local/bin) and no SUDO_* variables (flatpak --user, for one, refuses to run under sudo).
    shell = ("export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
             "unset SUDO_USER SUDO_UID SUDO_GID SUDO_COMMAND SUDO_HOME\n")
    return ("set -o pipefail\n" + shell + prelude + "{\nexec </dev/null\nexport AR_STDIN_ISOLATED=1\n"
            + script + "\n}\n")


def run_script(t: Target, script: str, *, env: dict[str, str] | None = None, timeout: float = 120,
               as_root: bool = True) -> proc.Result:
    """Run a bash script on the target. Env vars are exported in a prelude."""
    remote = "sudo -n bash -s" if as_root else "bash -s"
    return proc.run([*ssh_base(t), remote], input=_wrap(script, env), timeout=timeout)


def stream_script(t: Target, script: str, *, env: dict[str, str] | None = None, timeout: float = 3600,
                  on_line=None, log_file: Path | None = None, cancel=None) -> proc.Result:
    """Like run_script, but streams merged output line by line (long provisioning)."""
    return proc.stream([*ssh_base(t), "sudo -n bash -s"], input=_wrap(script, env), timeout=timeout,
                       on_line=on_line,
                       log_file=log_file, cancel=cancel)


def run_cmd(t: Target, command: str, *, timeout: float = 60, as_root: bool = True) -> proc.Result:
    return run_script(t, command + "\n", timeout=timeout, as_root=as_root)


class SSHConfigError(RuntimeError):
    """An SSH failure that retrying cannot fix (bad key, bad options)."""


_FATAL = ("too long for Unix domain socket", "Bad configuration option", "no such identity")


def reachable(t: Target, timeout: float = 15) -> bool:
    res = proc.run([*ssh_base(t), "true"], timeout=timeout)
    if not res.ok and any(f in res.err for f in _FATAL):
        raise SSHConfigError(f"ssh to {t.name} failed: {res.err.strip()[:300]}")
    return res.ok


def wait_reachable(t: Target, timeout: float = 600, interval: float = 5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if reachable(t):
            return True
        time.sleep(interval)
    return False


def boot_id(t: Target) -> str | None:
    res = run_cmd(t, "cat /proc/sys/kernel/random/boot_id", timeout=20, as_root=False)
    return res.out.strip() if res.ok else None


def close_master(t: Target) -> None:
    proc.run([*ssh_base(t)[:-1], "-O", "exit", f"{t.user}@{t.host}"], timeout=10)


# --- port forwards (code-server on localhost) -------------------------------------------------
def _tunnel_socket(label: str) -> Path:
    return _control_dir() / f"tunnel-{label}"


def tunnel_alive(label: str) -> bool:
    sock = _tunnel_socket(label)
    return sock.exists() and proc.run(["ssh", "-S", str(sock), "-O", "check", "tunnel"], timeout=10).ok


def free_local_port(preferred: int, tries: int = 50) -> int:
    for port in range(preferred, preferred + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise OSError(f"no free local port in {preferred}-{preferred + tries - 1}")


def open_tunnel(t: Target, label: str, local_port: int, remote_port: int) -> bool:
    """A background ssh forwarding 127.0.0.1:<local_port> on this host to the guest's
    127.0.0.1:<remote_port>. It outlives the caller (own session) until close_tunnel, or until
    the guest goes away (keepalives)."""
    if tunnel_alive(label):
        return True
    sock = _tunnel_socket(label)
    sock.unlink(missing_ok=True)
    opts: list[str] = []   # the shared options minus multiplexing: this ssh is its own master
    for flag, value in zip(SSH_OPTS[::2], SSH_OPTS[1::2], strict=True):
        if not value.startswith(("ControlMaster", "ControlPersist")):
            opts += [flag, value]
    cmd = ["ssh", *opts, "-o", "ExitOnForwardFailure=yes", "-M", "-S", str(sock), "-f", "-N",
           "-L", f"127.0.0.1:{local_port}:127.0.0.1:{remote_port}",
           "-i", str(t.key), "-p", str(t.port), f"{t.user}@{t.host}"]
    try:
        # ssh -f keeps running in the background: it must not hold our pipes open
        res = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, timeout=30, start_new_session=True)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return res.returncode == 0


def close_tunnel(label: str) -> None:
    sock = _tunnel_socket(label)
    if sock.exists():
        proc.run(["ssh", "-S", str(sock), "-O", "exit", "tunnel"], timeout=10)


def copy_to(t: Target, local: Path, remote_path: str, timeout: float = 600) -> proc.Result:
    """Copy a file to the guest (lands owned by root at remote_path)."""
    data = local.read_bytes()
    cmd = [*ssh_base(t), f"sudo -n install -D -m 0644 /dev/stdin {shlex.quote(remote_path)}"]
    import subprocess

    start = time.monotonic()
    p = subprocess.run(cmd, input=data, capture_output=True, timeout=timeout)
    return proc.Result(cmd, p.returncode, p.stdout.decode(errors="replace"),
                       p.stderr.decode(errors="replace"), time.monotonic() - start)


def upload(t: Target, items: dict[str, Path], remote_dir: str = "/var/tmp/ar-content",
           timeout: float = 1800) -> proc.Result:
    """Copy local files/directories into remote_dir/<name> (as the vagrant user)."""
    res = run_cmd(t, f"rm -rf {shlex.quote(remote_dir)}; install -d -o vagrant -m 0755 {shlex.quote(remote_dir)}",
                  timeout=60)
    if not res.ok:
        return res
    opts = [o for o in SSH_OPTS]
    for name, local in items.items():
        if not local.exists():
            continue
        dest = f"{t.user}@{t.host}:{remote_dir}/{name}"
        cmd = ["scp", "-r", "-q", *opts, "-o", f"ControlPath={t.control_path()}", "-i", str(t.key),
               "-P", str(t.port), str(local), dest]
        res = proc.run(cmd, timeout=timeout)
        if not res.ok:
            return res
    return res
