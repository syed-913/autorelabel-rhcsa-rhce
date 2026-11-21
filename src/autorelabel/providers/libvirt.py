"""libvirt operations: networks, pool, the lab VMs made from the box, power, pause, snapshots,
console. All objects we create are ledgered first."""

from __future__ import annotations

import ipaddress
import re
import time
from dataclasses import dataclass
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


def ensure_network(name: str, xml: str, tmpdir: Path, storage_dir: str | None,
                   dhcp_hosts: list[tuple[str, str]] | None = None) -> None:
    if not network_exists(name):
        ledger.record("libvirt-network", name, "lab network", storage_dir=storage_dir)
        f = tmpdir / f"{name}.xml"
        f.write_text(xml)
        virsh("net-define", str(f), check=True)
        f.unlink(missing_ok=True)
    if not network_active(name):
        virsh("net-start", name, check=True)
    if dhcp_hosts:
        sync_dhcp_hosts(name, dhcp_hosts)


def sync_dhcp_hosts(name: str, hosts: list[tuple[str, str]]) -> None:
    """Make an existing network reserve each (MAC, IP): a network created earlier (older
    version, other profile) can lack reservations or give an address to another MAC."""
    res = virsh("net-dumpxml", name, "--inactive", timeout=20)
    if not res.ok:
        return
    current = dict(re.findall(r"<host mac='([0-9a-fA-F:]+)' ip='([0-9.]+)'/>", res.out))
    owner = {ip: mac for mac, ip in current.items()}
    for mac, ip in hosts:
        if current.get(mac) == ip:
            continue
        for stale in {mac, owner.get(ip)} - {None}:
            if stale in current:
                virsh("net-update", name, "delete", "ip-dhcp-host",
                      f"<host mac='{stale}' ip='{current[stale]}'/>", "--live", "--config", check=True)
                owner.pop(current.pop(stale), None)
        virsh("net-update", name, "add", "ip-dhcp-host", f"<host mac='{mac}' ip='{ip}'/>",
              "--live", "--config", check=True)
        current[mac], owner[ip] = ip, mac


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
                f"libvirt pool {name!r} still points at the old lab storage, {existing}, not {path}. "
                "Set the lab storage directory back in Settings. To move it: run ./autorelabel uninstall "
                "(it keeps your ISO), then choose the new directory in the setup.")
    else:
        ledger.record("libvirt-pool", name, str(path), storage_dir=storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        virsh("pool-define-as", name, "dir", "--target", str(path), check=True)
    info = virsh("pool-info", name, timeout=20)
    if "running" not in info.out:
        virsh("pool-start", name, check=True)


# --- volumes (the box's base image, each VM's overlay and extra disks) ----------------------
# Base images: ours (BASE_PREFIX) and the ones vagrant-libvirt uploaded for earlier versions.
BASE_PREFIX = "autorelabel-rhel10-"
_VAGRANT_BASE = "autorelabel-VAGRANTSLASH-rhel10_vagrant_box_image_"


def qcow2_virtual_size(image: Path) -> int:
    """The disk size a qcow2 image presents to the guest (bytes 24-31 of its header)."""
    with open(image, "rb") as fh:
        head = fh.read(32)
    if len(head) < 32 or head[:4] != b"QFI\xfb":
        raise LibvirtError(f"{image} is not a qcow2 image")
    return int.from_bytes(head[24:32], "big")


def vol_list(pool: str) -> list[str]:
    """Volume names (vol-list has no --name: a table of name and path, two header lines)."""
    res = virsh("vol-list", "--pool", pool, timeout=30)
    rows = res.out.splitlines()[2:] if res.ok else []
    return [r.split()[0] for r in rows if r.strip()]


def vol_exists(pool: str, name: str) -> bool:
    return virsh("vol-info", "--pool", pool, name, timeout=20).ok


def vol_path(pool: str, name: str) -> str:
    return virsh("vol-path", "--pool", pool, name, timeout=20, check=True).out.strip()


def vol_backing(pool: str, name: str) -> str:
    """Path of the image a volume is an overlay of ('' for none)."""
    res = virsh("vol-dumpxml", "--pool", pool, name, timeout=20)
    m = re.search(r"<backingStore>.*?<path>([^<]+)</path>", res.out, re.S) if res.ok else None
    return m.group(1) if m else ""


def vol_delete(pool: str, name: str) -> proc.Result:
    return virsh("vol-delete", "--pool", pool, name, timeout=120)


def upload_base(pool: str, name: str, image: Path) -> None:
    """Copy the box's image into the pool as `name` (libvirt writes it, so the file belongs
    to libvirt like every other volume there)."""
    if vol_exists(pool, name):
        return
    virsh("vol-create-as", pool, name, str(qcow2_virtual_size(image)), "--format", "qcow2", check=True)
    res = virsh("vol-upload", "--pool", pool, name, str(image), timeout=1800)
    if not res.ok:
        vol_delete(pool, name)
        raise LibvirtError(f"could not copy the box into the storage pool: {res.tail(3)}")
    virsh("pool-refresh", pool, timeout=60)


def create_overlay(pool: str, name: str, base: str) -> None:
    """A VM's system disk: a qcow2 overlay on the base image (same size). A leftover one from
    an interrupted run is replaced."""
    if vol_exists(pool, name):
        vol_delete(pool, name)
    cap = virsh("vol-info", "--pool", pool, base, "--bytes", timeout=20, check=True).out
    size = re.search(r"Capacity:\s+(\d+)", cap)
    if not size:
        raise LibvirtError(f"no capacity for {base}")
    virsh("vol-create-as", pool, name, size.group(1), "--format", "qcow2",
          "--backing-vol", base, "--backing-vol-format", "qcow2", check=True)


def create_disk(pool: str, name: str, size_gb: int) -> None:
    """An empty extra disk (thin qcow2). A leftover one from an interrupted run is replaced."""
    if vol_exists(pool, name):
        vol_delete(pool, name)
    virsh("vol-create-as", pool, name, f"{size_gb}G", "--format", "qcow2", check=True)


def prune_base_volumes(pool: str, keep: str) -> list[str]:
    """Delete base images no volume is an overlay of any more, except `keep`: older builds of the
    box, and what vagrant-libvirt uploaded and never removed. Returns what was deleted."""
    names = vol_list(pool)
    used = {vol_backing(pool, v) for v in names}
    deleted = []
    for v in names:
        if v == keep or not (v.startswith(BASE_PREFIX) or v.startswith(_VAGRANT_BASE)):
            continue
        if vol_path(pool, v) not in used and vol_delete(pool, v).ok:
            deleted.append(v)
    return deleted


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


# --- making lab VMs from the box ----------------------------------------------------------------
# The same virtual hardware vagrant-libvirt 0.12 gave the lab VMs, in the same order, so the guests
# see the same devices and names (disks vda, vdb...; network cards in the same PCI slots). As with
# vagrant-libvirt, the machine type is libvirt's default, and the two network cards are attached
# after the domain is defined (that puts them after every other device).
@dataclass(frozen=True)
class VMSpec:
    name: str
    cpus: int
    memory_mb: int
    disks: list[tuple[str, int]]     # (name, size in GB) of the extra disks: vdb, vdc...
    mgmt_network: str
    mgmt_mac: str
    lab_network: str
    lab_mac: str
    iso: str = ""                    # a DVD on the SATA bus


def ensure_base(pool: str, version: str, image: Path) -> str:
    """The box's image in the pool (BASE_PREFIX + its version), copied there once."""
    name = f"{BASE_PREFIX}{version}.qcow2"
    upload_base(pool, name, image)
    return name


def _disk(path: str, dev: str) -> str:
    return (f"    <disk type='file' device='disk'>\n      <driver name='qemu' type='qcow2'/>\n"
            f"      <source file='{escape(path)}'/>\n      <target dev='{dev}' bus='virtio'/>\n    </disk>\n")


def domain_xml(spec: VMSpec, system_disk: str, extra_disks: list[str]) -> str:
    devs = _disk(system_disk, "vda")
    devs += "".join(_disk(p, f"vd{chr(ord('b') + i)}") for i, p in enumerate(extra_disks))
    if spec.iso:
        devs += ("    <disk type='file' device='cdrom'>\n      <driver name='qemu' type='raw'/>\n"
                 f"      <source file='{escape(spec.iso)}'/>\n      <target dev='hda' bus='sata'/>\n"
                 "      <readonly/>\n    </disk>\n")
    return f"""<domain type='kvm'>
  <name>{escape(spec.name)}</name>
  <description>autorelabel lab VM</description>
  <memory unit='KiB'>{spec.memory_mb * 1024}</memory>
  <currentMemory unit='KiB'>{spec.memory_mb * 1024}</currentMemory>
  <vcpu placement='static'>{spec.cpus}</vcpu>
  <os>
    <type arch='x86_64'>hvm</type>
    <boot dev='hd'/>
    <bootmenu enable='no'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <pae/>
  </features>
  <cpu mode='host-passthrough' check='none' migratable='on'/>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
{devs}    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <channel type='unix'>
      <target type='virtio' name='org.qemu.guest_agent.0'/>
    </channel>
    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>
    <graphics type='vnc' port='-1' autoport='yes' websocket='-1' listen='127.0.0.1' keymap='en-us'>
      <listen type='address' address='127.0.0.1'/>
    </graphics>
    <video>
      <model type='virtio' vram='16384' heads='1'/>
    </video>
    <rng model='virtio'>
      <backend model='random'>/dev/random</backend>
    </rng>
  </devices>
</domain>
"""


def interface_xml(network: str, mac: str) -> str:
    return (f"<interface type='network'>\n  <mac address='{escape(mac)}'/>\n"
            f"  <source network='{escape(network)}'/>\n  <model type='virtio'/>\n"
            "  <driver iommu='off'/>\n</interface>\n")


def create_vm(pool: str, base: str, spec: VMSpec, tmpdir: Path) -> None:
    """Define a lab VM: its system disk an overlay on the base image, empty extra disks, then the
    management and lab network cards. A leftover VM of the same name (an interrupted run) is
    removed first, with its disks."""
    if domain_exists(spec.name):
        destroy(spec.name)
        virsh("undefine", spec.name, "--remove-all-storage", "--snapshots-metadata", timeout=120)
    system = f"{spec.name}.img"
    create_overlay(pool, system, base)
    extra = []
    for i, (_disk_name, size_gb) in enumerate(spec.disks):
        vol = f"{spec.name}-vd{chr(ord('b') + i)}.qcow2"
        create_disk(pool, vol, size_gb)
        extra.append(vol_path(pool, vol))
    tmpdir.mkdir(parents=True, exist_ok=True)
    f = tmpdir / f"{spec.name}.xml"
    try:
        f.write_text(domain_xml(spec, vol_path(pool, system), extra))
        virsh("define", str(f), check=True)
        for net, mac in ((spec.mgmt_network, spec.mgmt_mac), (spec.lab_network, spec.lab_mac)):
            f.write_text(interface_xml(net, mac))
            virsh("attach-device", spec.name, str(f), "--config", check=True)
    finally:
        f.unlink(missing_ok=True)
