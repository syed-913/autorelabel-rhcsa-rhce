"""Read-only host preflight. Every failing check carries the exact commands for
the user's distro (from guides.py). The doctor never changes the host."""

from __future__ import annotations

import ipaddress
import os
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from . import guides, hostinfo, labspec, ledger, paths, proc, vagrant
from .config import Settings
from .fsutil import disk_free_bytes

MIN_VAGRANT = (2, 3)
MIN_PACKER = (1, 10)
MIN_VBOX = (7, 0)
VBOX_KVM_COEXIST = (7, 2, 2)
KERNEL_KVM_COEXIST = (6, 16)
OUR_BRIDGES = ("arbr-mgmt", "arbr-lab")


class Status(str, Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"


@dataclass
class Check:
    id: str
    title: str
    status: Status
    detail: str = ""
    fix: list[str] = field(default_factory=list)
    undo: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)   # guide keys behind `fix`

    @property
    def blocking(self) -> bool:
        return self.status is Status.FAIL


def _with_guide(check: Check, *keys: str) -> Check:
    for key in keys:
        for s in guides.with_prerequisites(key):
            if s.key in check.steps:
                continue
            check.steps.append(s.key)
            check.fix.append(f"# {s.title}")
            check.fix.extend(s.run)
            if s.note:
                check.fix.append(f"# note: {s.note}")
            check.undo.extend(s.undo)
    return check


# --- individual checks ---------------------------------------------------------

def check_platform() -> Check:
    if sys.platform != "linux" or hostinfo.is_wsl():
        return Check("platform", "Linux host", Status.FAIL,
                     "autorelabel v1 supports native Linux hosts only (Windows support is planned for v2).")
    import platform
    if platform.machine() != "x86_64":
        return Check("platform", "Linux host", Status.FAIL, f"x86_64 required, found {platform.machine()}")
    d = hostinfo.distro()
    return Check("platform", "Linux host", Status.OK,
                 f"{d.pretty} · kernel {platform.release()} · guidance: {guides.family_name()}")


def check_cpu() -> Check:
    missing = hostinfo.missing_v3_flags()
    flags = hostinfo.cpu_flags()
    virt = "vmx" in flags or "svm" in flags
    model = hostinfo.cpu_model()
    if missing:
        return Check("cpu", "CPU supports RHEL 10 (x86-64-v3)", Status.FAIL,
                     f"{model}: missing {', '.join(missing)}. RHEL 10 cannot boot on this CPU.")
    if not virt:
        return Check("cpu", "CPU supports RHEL 10 (x86-64-v3)", Status.FAIL,
                     f"{model}: hardware virtualization (VT-x/AMD-V) is not exposed. Enable it in the BIOS/UEFI.")
    return Check("cpu", "CPU supports RHEL 10 (x86-64-v3)", Status.OK, model)


def check_kvm() -> Check:
    dev = Path("/dev/kvm")
    if not dev.exists():
        return Check("kvm", "/dev/kvm available", Status.FAIL,
                     "KVM is not available. Enable virtualization in the BIOS/UEFI and load kvm_intel/kvm_amd.")
    if not os.access(dev, os.R_OK | os.W_OK):
        c = Check("kvm", "/dev/kvm available", Status.FAIL, "Your user cannot open /dev/kvm.")
        return _with_guide(c, "kvm_group")
    return Check("kvm", "/dev/kvm available", Status.OK, "read/write")


def check_ssh() -> Check:
    if proc.which("ssh"):
        return Check("ssh", "OpenSSH client", Status.OK, proc.which("ssh") or "")
    return _with_guide(Check("ssh", "OpenSSH client", Status.FAIL, "ssh not found"), "openssh")


def check_vagrant() -> Check:
    v = hostinfo.tool_version(["vagrant", "--version"])
    if v is None:
        return _with_guide(Check("vagrant", "Vagrant", Status.FAIL, "not installed"), "vagrant")
    text, ver = v
    if ver < MIN_VAGRANT:
        return _with_guide(Check("vagrant", "Vagrant", Status.FAIL,
                                 f"{text}: {'.'.join(map(str, MIN_VAGRANT))}+ required"), "vagrant")
    return Check("vagrant", "Vagrant", Status.OK, text)


def check_packer() -> Check:
    v = hostinfo.tool_version(["packer", "--version"])
    if v is None:
        return _with_guide(Check("packer", "Packer", Status.FAIL, "not installed"), "packer")
    text, ver = v
    if ver < MIN_PACKER:
        return _with_guide(Check("packer", "Packer", Status.FAIL,
                                 f"{text}: {'.'.join(map(str, MIN_PACKER))}+ required"), "packer")
    return Check("packer", "Packer", Status.OK, text.replace("Packer ", ""))


def check_libvirt() -> Check:
    if not proc.which("virsh"):
        return _with_guide(Check("libvirt", "libvirt (qemu:///system)", Status.FAIL, "virsh not found"), "libvirt")
    res = proc.run(["virsh", "-c", "qemu:///system", "uri"], timeout=20)
    if not res.ok:
        detail = res.tail(2) or "cannot connect to qemu:///system"
        c = Check("libvirt", "libvirt (qemu:///system)", Status.FAIL, detail)
        if "libvirt" not in hostinfo.user_groups():
            _with_guide(c, "libvirt_group")
        return _with_guide(c, "libvirt")
    missing = [b for b in ("qemu-img", "qemu-system-x86_64") if not proc.which(b)]
    if missing:
        return _with_guide(Check("libvirt", "libvirt (qemu:///system)", Status.FAIL,
                                 f"missing {', '.join(missing)} (needed to build the box)"), "libvirt")
    ver = proc.run(["virsh", "--version"], timeout=10).out.strip()
    return Check("libvirt", "libvirt (qemu:///system)", Status.OK, f"libvirt {ver}")


def check_libvirt_group() -> Check:
    if "libvirt" in hostinfo.user_groups() or os.getuid() == 0:
        return Check("libvirt_group", "Member of the libvirt group", Status.OK, "")
    if hostinfo.group_has_user_configured("libvirt"):
        return Check("libvirt_group", "Member of the libvirt group", Status.WARN,
                     "Added, but this login session predates it. Log out and back in.")
    return _with_guide(Check("libvirt_group", "Member of the libvirt group", Status.FAIL, ""), "libvirt_group")


def check_vagrant_plugins(provider: str) -> list[Check]:
    if not proc.which("vagrant"):
        return []
    plugins = vagrant.plugins()
    out = []
    if provider in ("libvirt", ""):
        if "vagrant-libvirt" in plugins:
            out.append(Check("vagrant_libvirt", "vagrant-libvirt plugin", Status.OK, plugins["vagrant-libvirt"]))
        else:
            st = Status.FAIL if provider == "libvirt" else Status.WARN
            out.append(_with_guide(Check("vagrant_libvirt", "vagrant-libvirt plugin", st, "not installed"),
                                   "vagrant_libvirt"))
    if "vagrant-registration" in plugins:
        out.append(Check("vagrant_registration", "vagrant-registration plugin", Status.INFO,
                         "Installed. autorelabel disables it for its labs, so you won't be asked for "
                         "Red Hat credentials."))
    return out


def check_virtualbox() -> Check:
    v = hostinfo.tool_version(["VBoxManage", "--version"])
    if v is None:
        return _with_guide(Check("virtualbox", "VirtualBox", Status.FAIL, "not installed"), "virtualbox")
    text, ver = v
    if ver < MIN_VBOX:
        return _with_guide(Check("virtualbox", "VirtualBox", Status.FAIL, f"{text}: 7.0+ required"), "virtualbox")
    kvm_loaded = hostinfo.module_loaded("kvm_intel") or hostinfo.module_loaded("kvm_amd")
    if kvm_loaded and hostinfo.kvm_virt_at_load():
        coexist = ver >= VBOX_KVM_COEXIST and hostinfo.kernel_version() >= KERNEL_KVM_COEXIST
        if not coexist:
            return Check(
                "virtualbox", "VirtualBox", Status.FAIL,
                f"{text}: KVM holds VT-x (kernel ≥ 6.12), so VirtualBox VMs won't start. Either use the "
                "libvirt provider, upgrade to VirtualBox ≥ 7.2.2 on kernel ≥ 6.16, or reboot with "
                "kvm.enable_virt_at_load=0.",
                fix=["# temporary (until reboot), only while no KVM VMs are running:",
                     "sudo modprobe -r kvm_intel kvm_amd 2>/dev/null; sudo modprobe -r kvm"],
            )
    if "vboxusers" not in hostinfo.user_groups():
        return _with_guide(Check("virtualbox", "VirtualBox", Status.WARN,
                                 f"{text}: you are not in the vboxusers group"), "virtualbox")
    return Check("virtualbox", "VirtualBox", Status.OK, text)


def check_memory(exam: str, profile: str) -> Check:
    need = labspec.required_memory_mb(exam, profile)
    avail = hostinfo.meminfo().get("MemAvailable", 0) // (1024 * 1024)
    title = f"Free memory for {exam.upper()} ({profile})"
    if avail >= need:
        return Check(f"memory_{exam}", title, Status.OK, f"{avail} MiB available, {need} MiB needed")
    hint = " Try the 'lite' profile." if profile == "standard" else " Close other VMs or applications."
    return Check(f"memory_{exam}", title, Status.WARN, f"{avail} MiB available, {need} MiB needed.{hint}")


def check_storage(settings: Settings, exam: str = "rhcsa") -> Check:
    title = "Lab storage directory"
    if not settings.storage_dir:
        return Check("storage", title, Status.INFO, "not chosen yet (the setup wizard asks)")
    base = Path(settings.storage_dir).expanduser()
    root = paths.storage_root(settings.storage_dir)
    if not base.exists():
        return Check("storage", title, Status.FAIL, f"{base} does not exist")
    if not os.access(base, os.W_OK) and not root.exists():
        return Check("storage", title, Status.FAIL, f"{base} is not writable by you")
    fstype = hostinfo.fs_type(base)
    if fstype in ("tmpfs", "ramfs", "nfs", "nfs4", "cifs", "smb3", "fuse.sshfs"):
        return Check("storage", title, Status.FAIL, f"{base} is on {fstype}; choose a local disk")
    free_gb = disk_free_bytes(base) / 1e9
    need = labspec.required_disk_gb(exam)
    if settings.provider == "libvirt":
        quser = hostinfo.qemu_user()
        if quser:
            blocked = hostinfo.blocked_ancestors(quser, root if root.exists() else base)
            if blocked:
                cmds = [f"setfacl -m u:{quser}:x '{d}'" for d in blocked]
                return Check("storage", title, Status.FAIL,
                             f"QEMU (user {quser}) cannot reach {base}.",
                             fix=["# allow QEMU to traverse these directories:", *cmds],
                             undo=[f"setfacl -x u:{quser} '{d}'" for d in blocked])
    if free_gb < need:
        return Check("storage", title, Status.WARN, f"{root}: {free_gb:.0f} GB free, ~{need} GB recommended")
    return Check("storage", title, Status.OK, f"{root} ({free_gb:.0f} GB free, {fstype})")


def check_iso(settings: Settings) -> Check:
    title = "RHEL 10 DVD ISO"
    if not settings.iso_path:
        return Check("iso", title, Status.INFO, "not chosen yet (the setup wizard asks)")
    iso = Path(settings.iso_path).expanduser()
    if not iso.is_file():
        return Check("iso", title, Status.FAIL, f"{iso} not found")
    vol = hostinfo.iso_volume_id(iso)
    ver = hostinfo.rhel_version_from_iso(vol)
    if not ver or not ver.startswith("10."):
        return Check("iso", title, Status.FAIL, f"{iso.name}: not a RHEL 10 DVD ISO (volume id {vol!r})")
    if iso.stat().st_size < 4_000_000_000:
        return Check("iso", title, Status.FAIL,
                     f"{iso.name} looks like the boot ISO; the full DVD ISO (8+ GB) is required")
    if settings.provider == "libvirt":
        quser = hostinfo.qemu_user()
        if quser:
            blocked = hostinfo.blocked_ancestors(quser, iso)
            if blocked or not hostinfo.account_can(quser, iso, "r"):
                targets = blocked or [iso]
                bit = "x" if blocked else "r"
                return Check("iso", title, Status.FAIL, f"QEMU (user {quser}) cannot read {iso}",
                             fix=[f"setfacl -m u:{quser}:{bit} '{t}'" for t in targets],
                             undo=[f"setfacl -x u:{quser} '{t}'" for t in targets])
    return Check("iso", title, Status.OK, f"RHEL {ver} · {iso}")


def check_subnets(settings: Settings) -> Check:
    ours = [ipaddress.IPv4Network(settings.mgmt_subnet), ipaddress.IPv4Network(settings.lab_subnet)]
    clashes = []
    for net, iface in hostinfo.host_routes():
        if iface in OUR_BRIDGES:
            continue
        for mine in ours:
            if net.overlaps(mine):
                clashes.append(f"{mine} overlaps {net} on {iface}")
    if clashes:
        return Check("subnets", "Lab networks don't collide", Status.FAIL, "; ".join(clashes),
                     fix=["# choose different subnets in Settings (mgmt / lab network)"])
    return Check("subnets", "Lab networks don't collide", Status.OK,
                 f"mgmt {settings.mgmt_subnet}, lab {settings.lab_subnet}")


def check_box(provider: str) -> Check:
    if not provider or not proc.which("vagrant"):
        return Check("box", "RHEL 10 box", Status.INFO, "")
    box = vagrant.has_box(provider)
    if box:
        return Check("box", "RHEL 10 box", Status.OK, f"{box.name} ({box.provider}, v{box.version})")
    return Check("box", "RHEL 10 box", Status.INFO, "not built yet (built once from your ISO, ~15 min)")


def check_leftovers() -> Check:
    entries = ledger.entries()
    if not entries:
        return Check("ledger", "Host footprint", Status.OK, "nothing created yet")
    kinds: dict[str, int] = {}
    for e in entries:
        kinds[e.kind] = kinds.get(e.kind, 0) + 1
    summary = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items()))
    return Check("ledger", "Host footprint", Status.INFO,
                 f"tracked for uninstall: {summary}")


def check_hypervisor_clash(provider: str) -> Check:
    from .providers import conflict

    title = "No VMs running under the other hypervisor"
    if not provider:
        return Check("hv_clash", title, Status.INFO, "checked once a provider is chosen")
    clash = conflict.check(provider)
    if clash:
        return Check("hv_clash", title, Status.WARN, f"{clash[0]}. {clash[1]}")
    return Check("hv_clash", title, Status.OK,
                 "KVM and VirtualBox VMs must never run at the same time; autorelabel checks before starting VMs")


def check_vbox_profile(settings: Settings) -> Check:
    from .providers import virtualbox as vb

    title = "VirtualBox free for the lab profile"
    home = paths.vbox_home(settings.storage_dir).resolve()
    if any(h != home for h in vb.service_homes()):
        return Check("vbox_profile", title, Status.WARN,
                     "VirtualBox Manager or your own VirtualBox VMs are running. " + vb.ProfileBusy.hint)
    return Check("vbox_profile", title, Status.OK, "lab VMs stay in autorelabel's own VirtualBox profile")


# --- orchestration -----------------------------------------------------------------

def run(settings: Settings, exam: str = "rhcsa") -> list[Check]:
    provider = settings.provider
    jobs: list[Callable[[], Check | list[Check]]] = [
        check_platform, check_cpu, check_ssh, check_vagrant, check_packer,
        lambda: check_vagrant_plugins(provider),
        lambda: check_memory(exam, settings.profile),
        lambda: check_storage(settings, exam),
        lambda: check_iso(settings),
        lambda: check_subnets(settings),
        lambda: check_box(provider),
        lambda: check_hypervisor_clash(provider),
        check_leftovers,
    ]
    if provider in ("libvirt", ""):
        jobs += [check_kvm, check_libvirt, check_libvirt_group]
    if provider in ("virtualbox", ""):
        jobs.append(check_virtualbox)
    if provider == "virtualbox" and settings.storage_dir:
        jobs.append(lambda: check_vbox_profile(settings))
    results: list[Check] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for out in pool.map(lambda f: f(), jobs):
            if isinstance(out, list):
                results.extend(out)
            else:
                results.append(out)
    if provider == "":
        # Provider not chosen yet: a failing provider is only a warning while the other works.
        lv_ok = all(c.status is not Status.FAIL for c in results
                    if c.id in ("kvm", "libvirt", "libvirt_group", "vagrant_libvirt"))
        vb_ok = all(c.status is not Status.FAIL for c in results if c.id == "virtualbox")
        if lv_ok or vb_ok:
            for c in results:
                if c.status is Status.FAIL and c.id in ("kvm", "libvirt", "libvirt_group",
                                                        "vagrant_libvirt", "virtualbox"):
                    c.status = Status.WARN
    order = ["platform", "cpu", "kvm", "ssh", "vagrant", "packer", "libvirt", "libvirt_group",
             "vagrant_libvirt", "virtualbox", "vagrant_registration", f"memory_{exam}", "storage",
             "iso", "subnets", "box", "hv_clash", "vbox_profile", "ledger"]
    results.sort(key=lambda c: order.index(c.id) if c.id in order else len(order))
    return results


def usable_providers(checks: list[Check]) -> list[str]:
    def ok(ids: tuple[str, ...]) -> bool:
        present = [c for c in checks if c.id in ids]
        return bool(present) and all(c.status in (Status.OK, Status.INFO, Status.WARN) and
                                     not (c.status is Status.WARN and c.fix) for c in present)
    out = []
    if ok(("kvm", "libvirt", "libvirt_group", "vagrant_libvirt")):
        out.append("libvirt")
    if ok(("virtualbox",)):
        out.append("virtualbox")
    return out


def blocking(checks: list[Check]) -> list[Check]:
    return [c for c in checks if c.blocking]
