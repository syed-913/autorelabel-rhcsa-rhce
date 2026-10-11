"""libvirt operations used outside Vagrant: networks, pool, power, pause,
snapshots, console. All objects we create are ledgered first."""

from __future__ import annotations

import ipaddress
import time
from pathlib import Path
from xml.sax.saxutils import escape

from .. import ledger, proc

URI = "qemu:///system"


class LibvirtError(RuntimeError):
    pass


def virsh(*args: str, timeout: float = 60, check: bool = False) -> proc.Result:
    res = proc.run(["virsh", "-c", URI, *args], timeout=timeout)
    if check and not res.ok:
        raise LibvirtError(f"virsh {' '.join(args[:2])}: {res.tail(3)}")
    return res


# --- networks -------------------------------------------------------------------------

def network_xml(name: str, bridge: str, subnet: str, *, dhcp_hosts: list[tuple[str, str]] | None = None,
                ipv6: str | None = None, dns: bool = False) -> str:
    net = ipaddress.IPv4Network(subnet)
    host_ip = net.network_address + 1
    lines = ["<network>", f"  <name>{escape(name)}</name>",
             f"  <bridge name='{bridge}' stp='on' delay='0'/>"]
    if not dns:
        lines.append("  <dns enable='no'/>")
    lines.append(f"  <ip address='{host_ip}' netmask='{net.netmask}'>")
    if dhcp_hosts is not None:
        lo, hi = net.network_address + 100, net.network_address + 200
        lines.append(f"    <dhcp><range start='{lo}' end='{hi}'/>")
        for mac, ip in dhcp_hosts:
            lines.append(f"      <host mac='{mac}' ip='{ip}'/>")
        lines.append("    </dhcp>")
    lines.append("  </ip>")
    if ipv6:
        lines.append(f"  <ip family='ipv6' address='{ipv6}1' prefix='64'/>")
    lines.append("</network>")
    return "\n".join(lines) + "\n"


def network_exists(name: str) -> bool:
    return virsh("net-info", name, timeout=20).ok


def network_active(name: str) -> bool:
    res = virsh("net-info", name, timeout=20)
    return res.ok and any(line.split()[:1] == ["Active:"] and line.split()[-1] == "yes"
                          for line in res.out.splitlines())


def ensure_network(name: str, xml: str, tmpdir: Path, storage_dir: str | None) -> None:
    if not network_exists(name):
        ledger.record("libvirt-network", name, "lab network", storage_dir=storage_dir)
        f = tmpdir / f"{name}.xml"
        f.write_text(xml)
        virsh("net-define", str(f), check=True)
        f.unlink(missing_ok=True)
    if not network_active(name):
        virsh("net-start", name, check=True)


def remove_network(name: str) -> None:
    virsh("net-destroy", name)
    virsh("net-undefine", name)


# --- storage pool -----------------------------------------------------------------------

def pool_exists(name: str) -> bool:
    return virsh("pool-info", name, timeout=20).ok


def pool_path(name: str) -> str | None:
    res = virsh("pool-dumpxml", name, timeout=20)
    if not res.ok:
        return None
    for line in res.out.splitlines():
        line = line.strip()
        if line.startswith("<path>"):
            return line.removeprefix("<path>").removesuffix("</path>")
    return None


def ensure_pool(name: str, path: Path, storage_dir: str | None) -> None:
    if pool_exists(name):
        existing = pool_path(name)
        if existing and Path(existing) != path:
            raise LibvirtError(
                f"libvirt pool {name!r} already exists at {existing}, not {path}. "
                "Run ./autorelabel uninstall (or change the storage directory back).")
    else:
        ledger.record("libvirt-pool", name, str(path), storage_dir=storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        virsh("pool-define-as", name, "dir", "--target", str(path), check=True)
    info = virsh("pool-info", name, timeout=20)
    if "running" not in info.out:
        virsh("pool-start", name, check=True)


# --- domains ------------------------------------------------------------------------------

def domain_exists(dom: str) -> bool:
    return virsh("dominfo", dom, timeout=20).ok


def state(dom: str) -> tuple[str, str]:
    """(state, reason) e.g. ('running', 'booted'), ('paused', 'I/O error'), ('shut off', 'shutdown')."""
    res = virsh("domstate", "--reason", dom, timeout=20)
    if not res.ok:
        return ("missing", "")
    text = res.out.strip().splitlines()[0] if res.out.strip() else ""
    if "(" in text:
        st, reason = text.split("(", 1)
        return st.strip(), reason.rstrip(")").strip()
    return text.strip(), ""


def start(dom: str) -> proc.Result:
    return virsh("start", dom, timeout=120)


def shutdown(dom: str, wait: float = 120) -> bool:
    virsh("shutdown", dom, timeout=30)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if state(dom)[0] == "shut off":
            return True
        time.sleep(2)
    return False


def destroy(dom: str) -> proc.Result:
    return virsh("destroy", dom, timeout=60)


def reset(dom: str) -> proc.Result:
    return virsh("reset", dom, timeout=30)


def ctrl_alt_del(dom: str) -> proc.Result:
    """systemd answers Ctrl+Alt+Del with a clean reboot, even in emergency mode."""
    return virsh("send-key", dom, "KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_DELETE", timeout=15)


def reboot_acpi(dom: str) -> proc.Result:
    return virsh("reboot", dom, "--mode", "acpi", timeout=30)


def suspend(dom: str) -> proc.Result:
    return virsh("suspend", dom, timeout=30)


def resume(dom: str) -> proc.Result:
    return virsh("resume", dom, timeout=30)


def time_sync(dom: str) -> proc.Result:
    """Reset the guest clock from the host via the guest agent (after a pause)."""
    return virsh("domtime", dom, "--sync", timeout=30)


def snapshot_create(dom: str, name: str, description: str = "") -> proc.Result:
    args = ["snapshot-create-as", dom, name]
    if description:
        args += ["--description", description]
    return virsh(*args, timeout=600)


def snapshot_revert(dom: str, name: str) -> proc.Result:
    return virsh("snapshot-revert", dom, name, "--force", timeout=600)


def snapshot_delete(dom: str, name: str) -> proc.Result:
    return virsh("snapshot-delete", dom, name, timeout=600)


def snapshots(dom: str) -> list[str]:
    res = virsh("snapshot-list", dom, "--name", timeout=30)
    return [s.strip() for s in res.out.splitlines() if s.strip()] if res.ok else []


def console_command(dom: str) -> list[str]:
    return ["virsh", "-c", URI, "console", "--force", dom]
