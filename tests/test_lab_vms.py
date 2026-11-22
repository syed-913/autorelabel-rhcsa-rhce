"""The lab VMs autorelabel makes from the box (no Vagrant): libvirt domains and volumes, VirtualBox
linked clones, the box's own files, boxes converted from Vagrant, and which SSH key a VM trusts."""

import json
import re
from pathlib import Path

import pytest

from autorelabel import box, paths, proc, vagrant_legacy
from autorelabel.config import Settings
from autorelabel.providers import libvirt as lv
from autorelabel.providers import virtualbox as vb

FIXTURES = Path(__file__).parent / "fixtures"


def _ok(out: str = "") -> proc.Result:
    return proc.Result([], 0, out, "", 0.0)


# --- libvirt ---------------------------------------------------------------------------------

def test_a_qcow2_images_size_comes_from_its_header(tmp_path):
    img = tmp_path / "box.qcow2"
    img.write_bytes(b"QFI\xfb" + b"\0" * 20 + (20 * 1024**3).to_bytes(8, "big") + b"\0" * 64)
    assert lv.qcow2_virtual_size(img) == 20 * 1024**3
    (tmp_path / "raw.img").write_bytes(b"\0" * 64)
    with pytest.raises(lv.LibvirtError):
        lv.qcow2_virtual_size(tmp_path / "raw.img")


def test_volumes_are_read_from_virshs_table(monkeypatch):
    """vol-list has no --name option (list and net-list do): its table is parsed."""
    table = (" Name              Path\n-----------------------------\n"
             " autorelabel-rhel10-1.qcow2   /pool/autorelabel-rhel10-1.qcow2\n"
             " autorelabel-rhcsa-node1.img  /pool/autorelabel-rhcsa-node1.img\n\n")
    calls = []
    monkeypatch.setattr(lv, "virsh", lambda *a, **k: calls.append(a) or _ok(table))
    assert lv.vol_list("autorelabel") == ["autorelabel-rhel10-1.qcow2", "autorelabel-rhcsa-node1.img"]
    assert "--name" not in calls[0]


def test_only_base_images_no_disk_uses_are_pruned(monkeypatch):
    vols = {
        "autorelabel-rhel10-2.qcow2": "",                        # the current box: kept
        "autorelabel-rhel10-1.qcow2": "",                        # an older build, unused: deleted
        "autorelabel-VAGRANTSLASH-rhel10_vagrant_box_image_0_9_box_0.img": "",   # left by vagrant-libvirt
        "autorelabel-VAGRANTSLASH-rhel10_vagrant_box_image_0_8_box_0.img": "",   # still under a lab
        "autorelabel-rhcsa-node1.img": "/pool/autorelabel-VAGRANTSLASH-rhel10_vagrant_box_image_0_8_box_0.img",
        "someone-elses.qcow2": "",                               # never touched
    }
    deleted = []
    monkeypatch.setattr(lv, "vol_list", lambda pool: list(vols))
    monkeypatch.setattr(lv, "vol_backing", lambda pool, v: vols[v])
    monkeypatch.setattr(lv, "vol_path", lambda pool, v: f"/pool/{v}")
    monkeypatch.setattr(lv, "vol_delete", lambda pool, v: deleted.append(v) or _ok())
    assert lv.prune_base_volumes("autorelabel", keep="autorelabel-rhel10-2.qcow2") == deleted
    assert sorted(deleted) == ["autorelabel-VAGRANTSLASH-rhel10_vagrant_box_image_0_9_box_0.img",
                               "autorelabel-rhel10-1.qcow2"]


def _spec(**kw) -> lv.VMSpec:
    base = dict(name="autorelabel-rhcsa-node1", cpus=1, memory_mb=1024, disks=[("disk1", 8), ("disk2", 4)],
                mgmt_network="autorelabel-mgmt", mgmt_mac="52:54:00:fa:01:0b",
                lab_network="autorelabel-lab", lab_mac="52:54:00:fb:01:0b")
    base.update(kw)
    return lv.VMSpec(**base)


def test_the_domain_has_vagrant_libvirts_devices_in_its_order():
    """libvirt gives the devices PCI slots in this order; the guests name their cards from the
    slots (fixtures: dumped from a lab Vagrant made). scripts/dev/check-domain-xml.py checks
    the outcome against libvirt itself."""
    xml = lv.domain_xml(_spec(), "/pool/node1.img", ["/pool/node1-vdb.qcow2", "/pool/node1-vdc.qcow2"])
    ref = (FIXTURES / "vagrant-libvirt-rhcsa-node1.xml").read_text()
    order = ["<disk", "<serial", "<console", "<channel", "<input type='mouse'", "<input type='keyboard'",
             "<graphics", "<video", "<rng"]
    assert [xml.index(t) for t in order] == sorted(xml.index(t) for t in order)
    assert re.findall(r"<target dev='(\w+)'", xml) == re.findall(r"<target dev='(\w+)'", ref) == ["vda", "vdb", "vdc"]
    assert "<interface" not in xml and "<address" not in xml and "machine=" not in xml
    assert "device='cdrom'" not in xml
    util = lv.domain_xml(_spec(disks=[], iso="/isos/rhel.iso"), "/pool/u.img", [])
    assert "<source file='/isos/rhel.iso'/>" in util and "bus='sata'" in util


def test_network_cards_are_attached_after_the_domain_management_first(monkeypatch, tmp_path):
    calls = []

    def fake(*args, **_kw):
        f = next((a for a in args if a.endswith(".xml")), "")
        calls.append((args[0], Path(f).read_text() if f else ""))
        return _ok("Capacity:       21474836480 bytes\n" if args[0] == "vol-info" else "/pool/x\n")

    monkeypatch.setattr(lv, "virsh", fake)
    monkeypatch.setattr(lv, "domain_exists", lambda d: False)
    monkeypatch.setattr(lv, "vol_exists", lambda p, n: False)
    lv.create_vm("autorelabel", "autorelabel-rhel10-1.qcow2", _spec(), tmp_path)
    verbs = [c[0] for c in calls if c[0] in ("define", "attach-device")]
    assert verbs == ["define", "attach-device", "attach-device"]
    nics = [c[1] for c in calls if c[0] == "attach-device"]
    assert "autorelabel-mgmt" in nics[0] and "52:54:00:fa:01:0b" in nics[0]
    assert "autorelabel-lab" in nics[1] and "52:54:00:fb:01:0b" in nics[1]
    made = [c for c in calls if c[0] == "vol-create-as"]
    assert len(made) == 3                                  # the overlay and two extra disks
    assert not list(tmp_path.iterdir())                    # the XML files are removed


# --- VirtualBox ---------------------------------------------------------------------------

def test_a_virtualbox_lab_vm_is_a_linked_clone_set_up_like_vagrants(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(vb, "vbm", lambda *a, **k: calls.append(a) or _ok())
    monkeypatch.setattr(vb, "domain_exists", lambda n: False)
    monkeypatch.setattr(vb, "_info", lambda n: {"Forwarding(0)": "packercomm,tcp,127.0.0.1,3456,,22"})
    monkeypatch.setattr(vb, "console_socket", lambda n: tmp_path / f"console-{n}.sock")
    spec = vb.VMSpec(name="autorelabel-rhcsa-node1", cpus=1, memory_mb=1024, disks=[("disk1", 8), ("disk2", 4)],
                     mgmt_mac="52:54:00:fa:01:0b", lab_if="vboxnet0", lab_mac="52:54:00:fb:01:0b", ssh_port=2223)
    vb.create_vm("autorelabel-base-1", spec, tmp_path / "vms", tmp_path / "disks")
    clone = calls[0]
    assert clone[:2] == ("clonevm", "autorelabel-base-1") and "link" in clone
    assert ("modifyvm", "autorelabel-rhcsa-node1", "--natpf1", "delete", "packercomm") in calls
    mod = next(c for c in calls if c[:1] == ("modifyvm",) and "--nic1" in c)

    def opt(name: str) -> str:
        return mod[mod.index(name) + 1]

    assert opt("--macaddress1") == "525400FA010B" and opt("--macaddress2") == "525400FB010B"
    assert opt("--natpf1") == "ssh,tcp,127.0.0.1,2223,,22" and opt("--hostonlyadapter2") == "vboxnet0"
    assert opt("--nat-localhostreachable1") == "off" and opt("--paravirt-provider") == vb.PARAVIRT
    assert opt("--uartmode1") == "server"
    attached = [c for c in calls if c[:1] == ("storageattach",)]
    assert [c[c.index("--port") + 1] for c in attached] == ["1", "2"]


def test_the_ssh_port_is_read_from_the_nat_rule():
    info = {"Forwarding(0)": "ssh,tcp,127.0.0.1,2201,,22", "Forwarding(1)": "web,tcp,,8080,,80"}
    vb_info = vb._info
    try:
        vb._info = lambda n: info
        assert vb.ssh_port("x") == 2201
        vb._info = lambda n: {}
        assert vb.ssh_port("x") is None
    finally:
        vb._info = vb_info


# --- the box --------------------------------------------------------------------------------

def _old_box(home: Path, provider: str) -> Path:
    """An autorelabel/rhel10 box as Vagrant 2.4 stores it (architecture folder included)."""
    folder = home / "boxes" / "autorelabel-VAGRANTSLASH-rhel10" / "0" / "amd64" / provider
    folder.mkdir(parents=True)
    if provider == "libvirt":
        (folder / "metadata.json").write_text(json.dumps({"disks": [{"format": "qcow2", "path": "box_0.img"}],
                                                          "provider": "libvirt"}))
        (folder / "box_0.img").write_bytes(b"QFI\xfb disk")
    else:
        (folder / "metadata.json").write_text(json.dumps({"provider": "virtualbox"}))
        (folder / "box.ovf").write_text("<Envelope/>")
        (folder / "box-disk001.vmdk").write_bytes(b"vmdk")
    keys = home / "insecure_private_keys"
    keys.mkdir(exist_ok=True)
    (keys / "vagrant.key.ed25519").write_text("KEY")
    return folder


@pytest.mark.parametrize("provider", ["libvirt", "virtualbox"])
def test_a_box_from_an_earlier_version_is_converted_once(tmp_path, monkeypatch, provider):
    home = tmp_path / "vagrant.d"
    _old_box(home, provider)
    monkeypatch.setenv("VAGRANT_HOME", str(home))
    forgot = []
    monkeypatch.setattr(vagrant_legacy, "forget_box", forgot.append)
    settings = Settings(provider=provider, storage_dir=str(tmp_path / "storage"))
    box.storage_layout(settings)["boxes"].mkdir(parents=True)
    assert box.box_status(settings, provider)[0] is True     # usable: converted on first use
    assert not box.installed(settings, provider)
    m = box.ensure_installed(settings, provider)
    assert box.installed(settings, provider) and forgot == [provider]
    assert m["format"] == box.BOX_FORMAT and m["converted_from"] == "vagrant 0"
    assert box.key_path(settings, provider).read_text() == "KEY"
    assert box.key_path(settings, provider).stat().st_mode & 0o777 == 0o600
    files = sorted(f.name for f in box.box_dir(settings, provider).iterdir())
    want = ["rhel10.qcow2", "ssh_key"] if provider == "libvirt" else ["box-disk001.vmdk", "rhel10.ovf", "ssh_key"]
    assert files == want
    box.ensure_installed(settings, provider)                 # nothing more to do
    assert forgot == [provider]


def test_no_box_at_all_says_build_it(tmp_path, monkeypatch):
    monkeypatch.setenv("VAGRANT_HOME", str(tmp_path / "nothing"))
    settings = Settings(provider="libvirt", storage_dir=str(tmp_path / "storage"))
    assert box.box_status(settings, "libvirt") == (False, "not built yet")
    with pytest.raises(box.BoxError) as exc:
        box.ensure_installed(settings, "libvirt")
    assert exc.value.user_fixable


def test_the_newest_old_box_is_found(tmp_path, monkeypatch):
    home = tmp_path / "vagrant.d"
    _old_box(home, "libvirt")
    newer = home / "boxes" / "autorelabel-VAGRANTSLASH-rhel10" / "10" / "libvirt"   # no architecture level
    newer.mkdir(parents=True)
    (newer / "metadata.json").write_text(json.dumps({"format": "qcow2"}))
    (newer / "box.img").write_bytes(b"QFI\xfb")
    monkeypatch.setenv("VAGRANT_HOME", str(home))
    old = vagrant_legacy.find_box("libvirt")
    assert old and old.version == "10" and list(old.files().values()) == ["rhel10.qcow2"]
    assert vagrant_legacy.find_box("virtualbox") is None


# --- SSH keys -------------------------------------------------------------------------------

def test_a_vm_is_reached_with_the_key_it_trusts(tmp_path, monkeypatch):
    from autorelabel import lab as lab_mod

    monkeypatch.setattr(lab_mod, "STATE_FILE", tmp_path / "lab.json")
    monkeypatch.setattr(paths, "VAGRANT_DOTFILE", tmp_path / "vagrant")
    settings = Settings(provider="libvirt", storage_dir=str(tmp_path / "storage"))
    lab = lab_mod.Lab(settings, "rhcsa")
    # a lab Vagrant made: the key Vagrant put in
    assert lab._key("node1") == tmp_path / "vagrant" / "rhcsa" / "machines" / "node1" / "libvirt" / "private_key"
    lab._set_key(["node1"], "box")
    assert lab._key("node1") == box.key_path(settings, "libvirt")
    lab._set_key(["node1"], "lab")
    assert lab._key("node1") == lab.key_file and lab.target("node1").key == lab.key_file
    assert lab.target("node1").host == lab.vm("node1").mgmt_ip


def test_a_lab_is_made_from_the_box_then_keyed(tmp_path, monkeypatch):
    from autorelabel import lab as lab_mod
    from autorelabel import remote

    monkeypatch.setattr(lab_mod, "STATE_FILE", tmp_path / "lab.json")
    monkeypatch.setattr(paths, "WORKSPACE", tmp_path / "ws")
    monkeypatch.setattr(paths, "TMP", tmp_path / "ws" / "tmp")
    settings = Settings(provider="libvirt", storage_dir=str(tmp_path / "storage"), iso_path=str(tmp_path / "x.iso"))
    lab = lab_mod.Lab(settings, "rhcsa")
    lab.key_file = tmp_path / "ws" / "keys" / "rhcsa" / "id_ed25519"
    events = []
    monkeypatch.setattr(lab, "guard_hypervisors", lambda: None)
    monkeypatch.setattr(lab_mod.ledger, "record", lambda *a, **k: None)
    monkeypatch.setattr(lab_mod.box, "ensure_installed", lambda s, p, step=None: {"version": "7"})
    monkeypatch.setattr(lab_mod.lv, "ensure_base", lambda pool, v, img: events.append(("base", v)) or f"b{v}")
    monkeypatch.setattr(lab_mod.lv, "create_vm", lambda pool, base, spec, tmp: events.append(("vm", spec.name, base)))
    monkeypatch.setattr(lab_mod.lv, "prune_base_volumes", lambda pool, keep: events.append(("prune", keep)))
    monkeypatch.setattr(lab.hv, "start", lambda d: events.append(("start", d)) or _ok())
    keys_seen = []
    monkeypatch.setattr(remote, "wait_reachable", lambda t, timeout=0: keys_seen.append(t.key) or True)
    monkeypatch.setattr(remote, "run_script",
                        lambda t, script, env=None, timeout=0: events.append(("key", t.name)) or _ok())
    monkeypatch.setattr(remote, "close_master", lambda t: None)
    lab.create(["node1", "node2"], lambda s: None, tmp_path / "up.log")
    assert events[:4] == [("base", "7"), ("vm", "autorelabel-rhcsa-node1", "b7"),
                          ("vm", "autorelabel-rhcsa-node2", "b7"), ("prune", "b7")]
    assert events[4:] == [("start", "autorelabel-rhcsa-node1"), ("start", "autorelabel-rhcsa-node2"),
                          ("key", "rhcsa-node1"), ("key", "rhcsa-node2")]
    assert lab.key_file.exists() and lab.state()["keys"] == {"node1": "lab", "node2": "lab"}
    box_key = box.key_path(settings, "libvirt")
    assert keys_seen == [box_key, lab.key_file, box_key, lab.key_file]   # box's key first, then the lab's


def test_a_running_virtualbox_lab_is_no_subnet_clash(monkeypatch):
    """vboxnet0 carries the lab subnet while lab VMs run: that is the lab's own network."""
    import ipaddress

    from autorelabel import doctor, hostinfo

    settings = Settings(provider="virtualbox")
    routes = [(ipaddress.IPv4Network(settings.lab_subnet), "vboxnet0")]
    monkeypatch.setattr(hostinfo, "host_routes", lambda: routes)
    assert doctor.check_subnets(settings).status is doctor.Status.OK
    routes.append((ipaddress.IPv4Network(settings.lab_subnet).supernet(), "wlp3s0"))   # someone else's
    assert doctor.check_subnets(settings).status is doctor.Status.FAIL
