"""Read-only facts about the host. Nothing here changes host state."""

from __future__ import annotations

import grp
import ipaddress
import os
import platform
import pwd
import re
import stat
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import proc

# x86-64-v3 (required by RHEL 10). Intel reports LZCNT as "abm" in /proc/cpuinfo.
X86_64_V3_FLAGS = ("avx", "avx2", "bmi1", "bmi2", "fma", "movbe", "f16c", "xsave")


RHEL_QEMU = "/usr/libexec/qemu-kvm"


def qemu_system() -> str | None:
    """QEMU for the box build: qemu-system-x86_64, or on RHEL-family hosts (which don't ship
    it) their qemu-kvm."""
    return proc.which("qemu-system-x86_64") or (RHEL_QEMU if os.access(RHEL_QEMU, os.X_OK) else None)


@dataclass(frozen=True)
class Distro:
    id: str
    like: tuple[str, ...]
    pretty: str
    version: str


@lru_cache(maxsize=1)
def distro() -> Distro:
    data: dict[str, str] = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                data[k] = v.strip().strip('"')
    except OSError:
        pass
    return Distro(
        id=data.get("ID", "unknown"),
        like=tuple(data.get("ID_LIKE", "").split()),
        pretty=data.get("PRETTY_NAME", platform.platform()),
        version=data.get("VERSION_ID", ""),
    )


def is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return bool(re.search(r"microsoft|wsl", Path("/proc/sys/kernel/osrelease").read_text(), re.I))
    except OSError:
        return False


@lru_cache(maxsize=1)
def cpu_flags() -> frozenset[str]:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("flags"):
                return frozenset(line.split(":", 1)[1].split())
    except OSError:
        pass
    return frozenset()


def missing_v3_flags() -> list[str]:
    flags = cpu_flags()
    missing = [f for f in X86_64_V3_FLAGS if f not in flags]
    if "lzcnt" not in flags and "abm" not in flags:
        missing.append("lzcnt")
    return missing


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown CPU"


def meminfo() -> dict[str, int]:
    """Values in bytes."""
    out: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, _, rest = line.partition(":")
            parts = rest.split()
            if parts and parts[0].isdigit():
                out[key] = int(parts[0]) * 1024
    except OSError:
        pass
    return out


def kernel_version() -> tuple[int, int]:
    m = re.match(r"(\d+)\.(\d+)", platform.release())
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def kvm_virt_at_load() -> bool | None:
    p = Path("/sys/module/kvm/parameters/enable_virt_at_load")
    try:
        return p.read_text().strip().upper() in ("Y", "1")
    except OSError:
        return None


def module_loaded(name: str) -> bool:
    try:
        return any(line.split()[0] == name for line in Path("/proc/modules").read_text().splitlines())
    except OSError:
        return False


def user_groups() -> set[str]:
    names = set()
    for gid in os.getgroups():
        try:
            names.add(grp.getgrgid(gid).gr_name)
        except KeyError:
            pass
    return names


def group_has_user_configured(group: str, user: str | None = None) -> bool:
    """True if the user is listed in the group database (even if this login
    session predates the change and os.getgroups() doesn't show it yet)."""
    user = user or pwd.getpwuid(os.getuid()).pw_name
    try:
        return user in grp.getgrnam(group).gr_mem
    except KeyError:
        return False


def version_tuple(text: str) -> tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not m:
        return ()
    return tuple(int(x) for x in m.groups() if x is not None)


def tool_version(cmd: list[str]) -> tuple[str, tuple[int, ...]] | None:
    if not proc.which(cmd[0]):
        return None
    res = proc.run(cmd, timeout=30)
    text = (res.out or res.err).strip().splitlines()
    first = text[0] if text else ""
    return first, version_tuple(first)


def qemu_user() -> str | None:
    """The account QEMU runs as under qemu:///system."""
    for name in ("libvirt-qemu", "qemu"):
        try:
            pwd.getpwnam(name)
            return name
        except KeyError:
            continue
    return None


def _acl_allows(path: Path, user: str, bit: str) -> bool:
    """Check POSIX ACL entries via getfacl (if installed)."""
    if not proc.which("getfacl"):
        return False
    res = proc.run(["getfacl", "-p", "--omit-header", str(path)], timeout=10)
    if not res.ok:
        return False
    try:
        pw = pwd.getpwnam(user)
        groups = {g.gr_name for g in grp.getgrall() if user in g.gr_mem}
        groups.add(grp.getgrgid(pw.pw_gid).gr_name)
    except KeyError:
        return False
    mask = "rwx"
    entries = []
    for line in res.out.splitlines():
        line = line.split("#")[0].strip()
        if line.startswith("mask::"):
            mask = line.split("::", 1)[1]
        elif line:
            entries.append(line)
    for e in entries:
        kind, qual, perms = (e.split(":") + ["", ""])[:3]
        if (kind == "user" and qual == user) or (kind == "group" and qual in groups):
            if bit in perms and bit in mask:
                return True
    return False


def account_can(user: str, path: Path, bit: str) -> bool:
    """Can `user` access `path` with permission bit 'r', 'w' or 'x' (mode + ACL)?"""
    try:
        st = path.stat()
        pw = pwd.getpwnam(user)
    except (OSError, KeyError):
        return False
    shift = {"r": 2, "w": 1, "x": 0}[bit]
    if pw.pw_uid == 0:
        return True
    if st.st_uid == pw.pw_uid:
        return bool(st.st_mode & (stat.S_IRWXU) & (1 << (6 + shift)))
    member_gids = {g.gr_gid for g in grp.getgrall() if user in g.gr_mem} | {pw.pw_gid}
    if st.st_gid in member_gids and st.st_mode & (1 << (3 + shift)):
        return True
    if st.st_mode & (1 << shift):
        return True
    return _acl_allows(path, user, bit)


def blocked_ancestors(user: str, target: Path) -> list[Path]:
    """Directories on the way to `target` that `user` cannot traverse."""
    target = target.resolve()
    blocked = []
    for d in reversed(target.parents):
        if d == Path("/"):
            continue
        if not account_can(user, d, "x"):
            blocked.append(d)
    return blocked


def fs_type(path: Path) -> str:
    """Filesystem type of the mount holding `path` (from /proc/mounts)."""
    p = path.resolve()
    while not p.exists():
        p = p.parent
    best, fstype = "", "unknown"
    try:
        for line in Path("/proc/mounts").read_text().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            mnt = parts[1].replace("\\040", " ")
            if (str(p) == mnt or str(p).startswith(mnt.rstrip("/") + "/")) and len(mnt) > len(best):
                best, fstype = mnt, parts[2]
    except OSError:
        pass
    return fstype


def host_routes() -> list[tuple[ipaddress.IPv4Network, str]]:
    """IPv4 routes from /proc/net/route as (network, interface)."""
    routes = []
    try:
        lines = Path("/proc/net/route").read_text().splitlines()[1:]
    except OSError:
        return routes
    for line in lines:
        f = line.split()
        if len(f) < 8:
            continue
        iface, dest_hex, mask_hex = f[0], f[1], f[7]
        dest = ipaddress.IPv4Address(bytes.fromhex(dest_hex)[::-1])
        mask = ipaddress.IPv4Address(bytes.fromhex(mask_hex)[::-1])
        if int(mask) == 0:
            continue
        net = ipaddress.IPv4Network(f"{dest}/{mask}", strict=False)
        routes.append((net, iface))
    return routes


def iso_volume_id(path: Path) -> str | None:
    """Read the ISO 9660 primary volume descriptor's volume identifier."""
    try:
        with open(path, "rb") as fh:
            fh.seek(16 * 2048)
            pvd = fh.read(2048)
    except OSError:
        return None
    if len(pvd) < 72 or pvd[1:6] != b"CD001":
        return None
    return pvd[40:72].decode("ascii", "replace").strip()


def rhel_version_from_iso(volume_id: str | None) -> str | None:
    m = re.match(r"RHEL-(\d+)-(\d+)", volume_id or "")
    return f"{m.group(1)}.{m.group(2)}" if m else None
