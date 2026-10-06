"""Facts about a lab (addresses, names, devices, service URLs) used to render
task text and passed to scripts as LAB_* environment variables."""

from __future__ import annotations

import ipaddress
from typing import Any

from . import labspec

DOMAIN = "lab.example.com"


def _disk_dev(provider: str, index: int) -> str:
    # index 0 is the root disk; extra disks start at 1
    letter = "abcdefghij"[index]
    return f"/dev/vd{letter}" if provider == "libvirt" else f"/dev/sd{letter}"


def build(exam: str, profile: str, provider: str, lab_subnet: str, mgmt_subnet: str,
          discovered: dict[str, Any] | None = None) -> dict[str, Any]:
    net = ipaddress.IPv4Network(lab_subnet)
    mgmt = ipaddress.IPv4Network(mgmt_subnet)
    host_ip = str(net.network_address + 1)
    third = str(net.network_address).split(".")[2]
    v6_prefix = f"fd00:{net.network_address.packed[1]:x}:{third}::"
    utility_ip = str(net.network_address + 10)
    facts: dict[str, Any] = {
        "domain": DOMAIN,
        "network": str(net),
        "prefix": net.prefixlen,
        "netmask": str(net.netmask),
        "gateway": host_ip,
        "dns": utility_ip,
        "ipv6_prefix": v6_prefix,
        "ipv6_prefixlen": 64,
        "utility_fqdn": f"utility.{DOMAIN}",
        "repo_baseos": f"http://utility.{DOMAIN}/rhel10/BaseOS",
        "repo_appstream": f"http://utility.{DOMAIN}/rhel10/AppStream",
        "repo_gpgkey": f"http://utility.{DOMAIN}/rhel10/RPM-GPG-KEY-redhat-release",
        "flatpak_repo": f"http://utility.{DOMAIN}/flatpak/repo",
        "flatpak_repofile": f"http://utility.{DOMAIN}/flatpak/lab.flatpakrepo",
        "ntp_server": f"utility.{DOMAIN}",
        "nfs_server": f"utility.{DOMAIN}",
        "provider": provider,
    }
    for vm in labspec.topology(exam, profile):
        entry: dict[str, Any] = {
            "name": vm.name,
            "fqdn": vm.fqdn,
            "ip": str(net.network_address + vm.host_octet),
            "ipv6": f"{v6_prefix}{vm.host_octet}",
            "mgmt_ip": str(mgmt.network_address + vm.host_octet),
            "nic": "the lab network interface",
        }
        for i, disk in enumerate(vm.disks, start=1):
            entry[disk.name] = _disk_dev(provider, i)
            entry[f"{disk.name}_gb"] = disk.size_gb
        facts[vm.name] = entry
    for node, values in (discovered or {}).items():
        if isinstance(values, dict) and node in facts:
            facts[node].update(values)
    return facts


def sample(exam: str = "rhcsa") -> dict[str, Any]:
    """Representative facts for linting and previews."""
    return build(exam, "standard", "libvirt", "172.25.250.0/24", "192.168.250.0/24")
