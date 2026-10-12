"""Never run VMs under KVM and VirtualBox at the same time.

On some kernel / VirtualBox combinations (seen with kernel 7.0 and VirtualBox 7.2.16), a
VirtualBox VM starting while KVM guests run corrupts KVM's CPU state ("kvm_intel: vmwrite
failed"): every KVM guest freezes and must be hard-reset. Starting lab VMs is therefore
refused while the other hypervisor has VMs running.
"""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

from .. import proc

# The processes VirtualBox runs a VM in (headless, VirtualBox Manager window, SDL).
VM_PROCESSES = {"VBoxHeadless", "VirtualBoxVM", "VBoxSDL"}


def running_virtualbox_vms(proc_root: Path = Path("/proc")) -> list[str]:
    """Running VirtualBox VMs of every user and profile, read from the process list. Asking
    VBoxManage instead would start a VBoxSVC for the profile asked about, which then serves
    every VBoxManage call for a few seconds (see virtualbox.wait_for_own_service)."""
    names: set[str] = set()
    for pid_dir in proc_root.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            if (pid_dir / "comm").read_text().strip() not in VM_PROCESSES:
                continue
            argv = (pid_dir / "cmdline").read_bytes().decode(errors="replace").split("\0")
        except OSError:
            continue
        args = dict(pairwise(argv))
        names.add(args.get("--comment") or args.get("--startvm") or f"process {pid_dir.name}")
    return sorted(names)


def running_kvm_domains() -> list[str]:
    if not proc.which("virsh"):
        return []
    res = proc.run(["virsh", "-c", "qemu:///system", "list", "--name"], timeout=30)
    return [ln.strip() for ln in res.out.splitlines() if ln.strip()] if res.ok else []


def check(provider: str) -> tuple[str, str] | None:
    """(message, hint) if starting VMs with `provider` now would clash with the other hypervisor."""
    if provider == "libvirt":
        other = running_virtualbox_vms()
        if other:
            return (f"VirtualBox VMs are running: {', '.join(other)}",
                    "KVM and VirtualBox VMs must not run at the same time (KVM guests can freeze). "
                    "Shut the VirtualBox VMs down, then retry.")
    elif provider == "virtualbox":
        other = running_kvm_domains()
        if other:
            return (f"KVM/libvirt VMs are running: {', '.join(other)}",
                    "KVM and VirtualBox VMs must not run at the same time (the KVM guests can freeze). "
                    "Shut the libvirt VMs down (virsh shutdown <name>), then retry.")
    return None
