#!/usr/bin/env python3
"""Check that the lab VMs autorelabel defines get the same virtual hardware vagrant-libvirt gave
them (tests/fixtures/vagrant-libvirt-rhcsa-*.xml, dumped from a lab Vagrant made in 1.4.2): same
devices, same PCI slots, so the guests see the same disk and network card names.

Needs libvirt (qemu:///system). It defines throwaway domains named autorelabel-xmlcheck-*, never
starts them, and removes them again.

    PYTHONPATH=src python scripts/dev/check-domain-xml.py
"""
import difflib
import re
import sys
import tempfile
from pathlib import Path

from autorelabel import labspec
from autorelabel.providers import libvirt as lv

tmp = Path(tempfile.mkdtemp(prefix="xmlcheck-"))
fixtures = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
iso = "REPO/rhel-10.0-x86_64-dvd.iso"
def norm(xml, name):
    xml = re.sub(r"<uuid>[^<]*</uuid>", "<uuid>UUID</uuid>", xml)
    xml = re.sub(r"<description>[^<]*</description>", "<description/>", xml)
    xml = xml.replace(f"autorelabel-xmlcheck-{name}", f"autorelabel-rhcsa-{name}")
    xml = re.sub(r"\s*<alias name='ua-[^']*'/>", "", xml)
    return xml
ok = True
for vm in labspec.topology("rhcsa", "lite"):
    o = vm.host_octet
    dom = f"autorelabel-xmlcheck-{vm.name}"
    spec = lv.VMSpec(name=dom, cpus=vm.cpus, memory_mb=vm.memory_mb, disks=[(d.name, d.size_gb) for d in vm.disks],
                     mgmt_network="autorelabel-mgmt", mgmt_mac=f"52:54:00:fa:01:{o:02x}",
                     lab_network="autorelabel-lab", lab_mac=f"52:54:00:fb:01:{o:02x}",
                     iso=iso if vm.role == "utility" else "")
    extra = [f"POOL/autorelabel-rhcsa-{vm.name}-vd{chr(98+i)}.qcow2" for i in range(len(vm.disks))]
    f = tmp / f"{dom}.xml"
    f.write_text(lv.domain_xml(spec, f"POOL/autorelabel-rhcsa-{vm.name}.img", extra))
    lv.virsh("define", str(f), check=True)
    try:
        for net, mac in ((spec.mgmt_network, spec.mgmt_mac), (spec.lab_network, spec.lab_mac)):
            f.write_text(lv.interface_xml(net, mac))
            lv.virsh("attach-device", dom, str(f), "--config", check=True)
        mine = norm(lv.virsh("dumpxml", "--inactive", dom, check=True).out, vm.name)
    finally:
        lv.virsh("undefine", dom)
        f.unlink(missing_ok=True)
    ref = norm((fixtures / f"vagrant-libvirt-rhcsa-{vm.name}.xml").read_text(), vm.name)
    if mine.strip() == ref.strip():
        print(f"{vm.name}: identical")
    else:
        ok = False
        print(f"{vm.name}: DIFFERS")
        print("".join(difflib.unified_diff(ref.splitlines(True), mine.splitlines(True), "vagrant", "ours")))
tmp.rmdir()
print("identical to vagrant-libvirt" if ok else "DIFFERENT from vagrant-libvirt")
sys.exit(0 if ok else 1)
