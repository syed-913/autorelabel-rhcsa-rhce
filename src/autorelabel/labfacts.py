"""Facts about a lab (addresses, names, devices, service URLs) used to render
task text and passed to scripts as LAB_* environment variables."""

from __future__ import annotations

import ipaddress
from typing import Any

from . import labspec

DOMAIN = "lab.example.com"

# RHCE inventory groups the candidate builds (ansible-setup anchor). The lite profile has
# three managed nodes, so balancers share node2 with test (never with the web servers).
RHCE_GROUPS = {
    "standard": {"dev": ["node1"], "test": ["node2"], "prod": ["node3", "node4"], "balancers": ["node5"]},
    "lite": {"dev": ["node1"], "test": ["node2"], "prod": ["node3"], "balancers": ["node2"]},
}
RHCE_PARENT = ("webservers", "prod")       # webservers has prod as a child group
CONTROL_USER = "student"
PROJECT_DIR = "/home/student/ansible"
EE_IMAGE = "utility.lab.example.com:5000/ee-autorelabel:latest"


def _rhce_facts(profile: str) -> dict[str, Any]:
    groups = RHCE_GROUPS[profile]
    managed = sorted({h for hosts in groups.values() for h in hosts}, key=lambda n: int(n[4:]))
    flat = {g: " ".join(h) for g, h in groups.items()}
    flat[RHCE_PARENT[0]] = flat[RHCE_PARENT[1]]
    flat["all"] = " ".join(managed)
    lines = []
    for g, hosts in groups.items():
        lines.append(f"- {', '.join(f'`{h}.{DOMAIN}`' for h in hosts)} → group **{g}**")
    lines.append(f"- the **{RHCE_PARENT[0]}** group has the **{RHCE_PARENT[1]}** group as a child group")
    web = f"http://utility.{DOMAIN}/ansible"
    return {
        "groups": flat,
        "inventory_md": "\n".join(lines),
        "control_user": CONTROL_USER,
        "project_dir": PROJECT_DIR,
        "ee_image": EE_IMAGE,
        "git_url": f"http://utility.{DOMAIN}/git/ansible.git",
        "git_content_url": f"http://utility.{DOMAIN}/git/lab-content.git",
        "roles_url": f"{web}/roles",
        "collections_url": f"{web}/collections",
    }


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
        # kernel names of the first three disks (root, disk1, an absent third disk)
        "disk_a": _disk_dev(provider, 0)[5:],
        "disk_b": _disk_dev(provider, 1)[5:],
        "disk_c": _disk_dev(provider, 2)[5:],
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
    if exam == "rhce":
        facts.update(_rhce_facts(profile))
    for node, values in (discovered or {}).items():
        if isinstance(values, dict) and node in facts:
            facts[node].update(values)
    return facts


def sample(exam: str = "rhcsa", profile: str = "standard") -> dict[str, Any]:
    """Representative facts for linting and previews."""
    return build(exam, profile, "libvirt", "172.25.250.0/24", "192.168.250.0/24")


def script_nodes(target: str, facts: dict[str, Any]) -> list[str]:
    """Nodes a `setup@<target>.sh` / `solution@<target>.sh` runs on: a node name, or an RHCE
    inventory group name (`setup@all.sh`, `setup@prod.sh`) for every host in that group."""
    groups = facts.get("groups", {})
    if target not in facts and target in groups:
        return list(groups[target].split())
    return [target]


def check_nodes(on: str | None, default: str, facts: dict[str, Any]) -> list[str]:
    """Where a check runs: a node name, or `@group` for every host in an inventory group."""
    target = on or default
    if target.startswith("@"):
        return list(facts.get("groups", {}).get(target[1:], "").split())
    return [target]
