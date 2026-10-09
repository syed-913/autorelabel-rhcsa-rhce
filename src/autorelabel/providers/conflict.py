"""Never run VMs under KVM and VirtualBox at the same time.

On some kernel / VirtualBox combinations (seen with kernel 7.0 and VirtualBox 7.2.16), a
VirtualBox VM starting while KVM guests run corrupts KVM's CPU state ("kvm_intel: vmwrite
failed"): every KVM guest freezes and must be hard-reset. Starting lab VMs is therefore
refused while the other hypervisor has VMs running.
"""

from __future__ import annotations

import os

from .. import proc


def running_virtualbox_vms() -> list[str]:
    """Running VirtualBox VMs in the user's default profile and in autorelabel's profile."""
    if not proc.which("VBoxManage"):
        return []
    names: list[str] = []
    homes = [None, os.environ.get("VBOX_USER_HOME")]
    for home in dict.fromkeys(homes):
        env = dict(os.environ)
        env.pop("VBOX_USER_HOME", None)
        if home:
            env["VBOX_USER_HOME"] = home
        res = proc.run(["VBoxManage", "list", "runningvms"], timeout=30, env=env)
        names += [ln.split('"')[1] for ln in res.out.splitlines() if ln.count('"') >= 2]
    return sorted(set(names))


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
