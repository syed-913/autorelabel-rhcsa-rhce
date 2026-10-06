"""Host helpers: ledger, atomic files, version parsing, ISO labels, vagrant parsing."""

from __future__ import annotations

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
