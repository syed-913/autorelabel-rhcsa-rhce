"""Host helpers: ledger, atomic files, version parsing, ISO labels, vagrant parsing."""

from __future__ import annotations

import pytest

from autorelabel import fsutil, hostinfo, ledger, paths, vagrant


def test_ledger_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "LEDGER_FILE", tmp_path / "ledger.tsv")
    ledger.record("libvirt-pool", "autorelabel", "pool\twith tab")
    ledger.record("libvirt-pool", "autorelabel", "duplicate is ignored")
    ledger.record("dir", "/x/autorelabel", "")
    entries = ledger.entries()
    assert [(e.kind, e.ident) for e in entries] == [("libvirt-pool", "autorelabel"), ("dir", "/x/autorelabel")]
    assert "\t" not in entries[0].details
    line = (tmp_path / "ledger.tsv").read_text().splitlines()[0]
    assert len(line.split("\t")) == 4  # bash-parsable


def test_ledger_rejects_unknown_kind(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "LEDGER_FILE", tmp_path / "ledger.tsv")
    try:
        ledger.record("nonsense", "x")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_atomic_write_and_lock(tmp_path):
    target = tmp_path / "a" / "state.json"
    fsutil.atomic_write_json(target, {"x": 1})
    assert fsutil.read_json(target) == {"x": 1}
    assert not [p for p in target.parent.iterdir() if p.name.startswith(".state.json.")]
    lock = tmp_path / "lock"
    with fsutil.file_lock(lock):
        try:
            with fsutil.file_lock(lock):
                raise AssertionError("second lock should fail")
        except fsutil.LockBusy:
            pass


def test_version_tuple():
    assert hostinfo.version_tuple("Vagrant 2.4.9") == (2, 4, 9)
    assert hostinfo.version_tuple("Packer v1.16.1") == (1, 16, 1)
    assert hostinfo.version_tuple("7.2.16r174877") == (7, 2, 16)
    assert hostinfo.version_tuple("nothing") == ()


def test_iso_volume_id(tmp_path):
    iso = tmp_path / "fake.iso"
    pvd = bytearray(2048)
    pvd[0] = 1
    pvd[1:6] = b"CD001"
    pvd[40:72] = b"RHEL-10-0-BaseOS-x86_64".ljust(32)
    iso.write_bytes(bytes(16 * 2048) + bytes(pvd))
    vol = hostinfo.iso_volume_id(iso)
    assert vol == "RHEL-10-0-BaseOS-x86_64"
    assert hostinfo.rhel_version_from_iso(vol) == "10.0"
    assert hostinfo.rhel_version_from_iso("Fedora-41") is None


def test_vagrant_machine_readable():
    out = (
        "1791314412,,ui,info,vagrant-libvirt (0.12.2%!(VAGRANT_COMMA) global)\n"
        "1791314412,,plugin-name,vagrant-libvirt\n"
        "1791314412,vagrant-libvirt,plugin-version,0.12.2%!(VAGRANT_COMMA) global\n"
    )
    rows = vagrant.parse_machine_readable(out)
    assert ("vagrant-libvirt", "plugin-version", ["0.12.2, global"]) in rows


def _fake_proc(root, pid: str, comm: str, environ: str = "", cmdline: str = "") -> None:
    d = root / pid
    d.mkdir()
    (d / "comm").write_text(comm + "\n")
    (d / "environ").write_bytes(environ.replace(" ", "\0").encode())
    (d / "cmdline").write_bytes(cmdline.replace(" ", "\0").encode())


def test_vboxsvc_profiles_are_detected(tmp_path):
    from autorelabel.providers import virtualbox as vb

    ours = tmp_path / "profile"
    _fake_proc(tmp_path, "100", "VBoxSVC", f"HOME=/home/u VBOX_USER_HOME={ours}")
    _fake_proc(tmp_path, "200", "bash", "HOME=/home/u")
    (tmp_path / "self").mkdir()
    assert vb.service_homes(tmp_path) == [ours.resolve()]
    vb.wait_for_own_service(ours, timeout=0, proc_root=tmp_path)       # ours: no wait
    _fake_proc(tmp_path, "101", "VBoxSVC", "HOME=/home/u")             # the user's default profile
    with pytest.raises(vb.ProfileBusy):
        vb.wait_for_own_service(ours, timeout=0, proc_root=tmp_path)


def test_running_virtualbox_vms_from_processes(tmp_path):
    from autorelabel.providers import conflict

    _fake_proc(tmp_path, "300", "VBoxHeadless", cmdline="/usr/lib/virtualbox/VBoxHeadless --comment "
               "autorelabel-rhcsa-node1 --startvm 1b2c --vrde config")
    _fake_proc(tmp_path, "301", "VirtualBoxVM", cmdline="/usr/lib/virtualbox/VirtualBoxVM --startvm win11")
    _fake_proc(tmp_path, "302", "VBoxSVC", cmdline="/usr/lib/virtualbox/VBoxSVC --auto-shutdown")
    assert conflict.running_virtualbox_vms(tmp_path) == ["autorelabel-rhcsa-node1", "win11"]


def test_virtualbox_vms_start_without_the_kvm_clock(monkeypatch):
    from autorelabel import proc
    from autorelabel.providers import virtualbox as vb

    calls = []
    fails = {"modifyvm": 1}           # the first try finds the VM's session still closing

    def fake_vbm(*args, **_kw):
        calls.append(args)
        ok = not fails.get(args[0])
        fails[args[0]] = 0
        return proc.Result(list(args), 0 if ok else 1, "", "", 0.0)

    monkeypatch.setattr(vb, "vbm", fake_vbm)
    monkeypatch.setattr(vb, "ensure_console_keeper", lambda: None)
    monkeypatch.setattr(vb.time, "sleep", lambda _s: None)
    assert vb.start("autorelabel-rhcsa-node1").ok
    assert calls == [("modifyvm", "autorelabel-rhcsa-node1", "--paravirt-provider", "minimal")] * 2 + \
        [("startvm", "autorelabel-rhcsa-node1", "--type", "headless")]
