"""Lab topologies: which VMs exist for each exam and resource profile."""

from __future__ import annotations

from dataclasses import dataclass, field

EXAMS = ("rhcsa", "rhce")


@dataclass(frozen=True)
class Disk:
    name: str          # logical name used in tasks: "disk1", "disk2"
    size_gb: int


@dataclass(frozen=True)
class VM:
    name: str          # vagrant machine name and short hostname
    role: str          # utility | exam | control | managed
    cpus: int
    memory_mb: int
    host_octet: int    # last octet on both the mgmt and the lab network
    disks: tuple[Disk, ...] = field(default_factory=tuple)

    @property
    def fqdn(self) -> str:
        return f"{self.name}.lab.example.com"


def _rhcsa(profile: str) -> tuple[VM, ...]:
    mem = {"lite": (768, 1024), "standard": (1024, 1536)}[profile]
    return (
        VM("utility", "utility", 1, mem[0], 10),
        VM("node1", "exam", 1, mem[1], 11, (Disk("disk1", 8), Disk("disk2", 4))),
        VM("node2", "exam", 1, mem[1], 12, (Disk("disk1", 4),)),
    )


def _rhce(profile: str) -> tuple[VM, ...]:
    if profile == "lite":
        util, ctl, managed, count = 1024, 2048, 768, 3
    else:
        util, ctl, managed, count = 1024, 2560, 1024, 5
    vms = [VM("utility", "utility", 1, util, 10), VM("control", "control", 2, ctl, 20)]
    for i in range(1, count + 1):
        vms.append(VM(f"node{i}", "managed", 1, managed, 20 + i, (Disk("disk1", 4),)))
    return tuple(vms)


def topology(exam: str, profile: str) -> tuple[VM, ...]:
    if exam == "rhcsa":
        return _rhcsa(profile)
    if exam == "rhce":
        return _rhce(profile)
    raise ValueError(f"unknown exam {exam!r}")


HOST_MARGIN_MB = 768  # leave room for the host itself


def required_memory_mb(exam: str, profile: str) -> int:
    return sum(vm.memory_mb for vm in topology(exam, profile)) + HOST_MARGIN_MB


def required_disk_gb(exam: str) -> int:
    # box volume + overlays + sparse disks actually used + snapshots, generous
    return 30 if exam == "rhcsa" else 40
