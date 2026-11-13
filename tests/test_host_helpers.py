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
    # and without a way to the host's own 127.0.0.1 through the NAT gateway (10.0.2.2)
    assert calls == [("modifyvm", "autorelabel-rhcsa-node1", "--paravirt-provider", "minimal",
                      "--nat-localhostreachable1", "off")] * 2 + \
        [("startvm", "autorelabel-rhcsa-node1", "--type", "headless")]


def test_a_virtualbox_vm_whose_settings_were_refused_is_not_started(monkeypatch):
    """The settings carry the closed way to the host's 127.0.0.1: a VM that did not get them
    stays off, and the person is told why."""
    from autorelabel import proc
    from autorelabel.lab import LabError
    from autorelabel.providers import virtualbox as vb

    calls = []

    def fake_vbm(*args, **_kw):
        calls.append(args[0])
        refused = args[0] == "modifyvm"
        err = "VBoxManage: error: The machine is locked" if refused else ""
        return proc.Result(list(args), 1 if refused else 0, "", err, 0.0)

    monkeypatch.setattr(vb, "vbm", fake_vbm)
    monkeypatch.setattr(vb, "ensure_console_keeper", lambda: None)
    monkeypatch.setattr(vb.time, "sleep", lambda _s: None)
    with pytest.raises(LabError) as caught:
        vb.start("autorelabel-rhcsa-node1")
    assert calls == ["modifyvm"] * vb.MODIFY_TRIES            # and no startvm
    assert "autorelabel-rhcsa-node1 was not started" in str(caught.value)
    assert "The machine is locked" in str(caught.value)
    assert caught.value.hint
    # the grader's power-cycle goes through the same door
    monkeypatch.setattr(vb, "shutdown", lambda _name, wait=0: True)
    with pytest.raises(LabError):
        vb.reboot_acpi("autorelabel-rhcsa-node1")
    assert "startvm" not in calls


def test_no_virtualbox_lab_vm_keeps_the_way_to_the_hosts_loopback():
    """The box build needs it (the kickstart comes from 10.0.2.2); the box and the lab must not
    keep it: with it on, a lab VM reads whatever listens on this computer's 127.0.0.1."""
    from autorelabel import paths

    packer = (paths.PACKER_DIR / "rhel10.pkr.hcl").read_text()
    post = packer[packer.index("vboxmanage_post = ["):]
    assert '"--nat-localhostreachable1", "off"' in post[:post.index("\n  ]")]
    vagrantfile = (paths.VAGRANT_DIR / "Vagrantfile").read_text()
    assert 'vb.customize ["modifyvm", :id, "--nat-localhostreachable1", "off"]' in vagrantfile


def test_the_lab_network_gets_no_virtualbox_dhcp(monkeypatch):
    from autorelabel import proc
    from autorelabel.providers import virtualbox as vb

    calls = []
    servers = "NetworkName:    HostInterfaceNetworking-vboxnet0\nDhcpd IP:       192.168.56.100\n"

    def fake_vbm(*args, **_kw):
        calls.append(args)
        return proc.Result(list(args), 0, servers if args[:2] == ("list", "dhcpservers") else "", "", 0.0)

    monkeypatch.setattr(vb, "vbm", fake_vbm)
    assert vb.remove_dhcp_server("vboxnet0")
    assert calls[-1] == ("dhcpserver", "remove", "--network=HostInterfaceNetworking-vboxnet0")
    calls.clear()
    assert not vb.remove_dhcp_server("vboxnet1")      # none there: nothing removed
    assert calls == [("list", "dhcpservers")]


def test_rhel_hosts_build_with_qemu_kvm(monkeypatch):
    """RHEL-family hosts ship /usr/libexec/qemu-kvm instead of qemu-system-x86_64."""
    from autorelabel import proc

    monkeypatch.setattr(proc, "which", lambda name: None)
    monkeypatch.setattr(hostinfo.os, "access", lambda path, mode: path == hostinfo.RHEL_QEMU)
    assert hostinfo.qemu_system() == hostinfo.RHEL_QEMU
    monkeypatch.setattr(hostinfo.os, "access", lambda path, mode: False)
    assert hostinfo.qemu_system() is None
    monkeypatch.setattr(proc, "which", lambda name: f"/usr/bin/{name}")
    assert hostinfo.qemu_system() == "/usr/bin/qemu-system-x86_64"


def test_fixes_the_user_ran_are_ledgered_for_uninstall(tmp_path, monkeypatch):
    from autorelabel import doctor

    monkeypatch.setattr(paths, "WORKSPACE", tmp_path)
    monkeypatch.setattr(paths, "LEDGER_FILE", tmp_path / "ledger.tsv")
    failing = doctor.Check("libvirt_group", "libvirt group", doctor.Status.FAIL,
                           fix=["sudo usermod -aG libvirt $USER"], undo=["sudo gpasswd -d $USER libvirt"])
    doctor.remember_user_actions([failing])
    assert ledger.entries() == []                          # shown, not run yet: nothing to undo
    fixed = doctor.Check("libvirt_group", "libvirt group", doctor.Status.OK)
    doctor.remember_user_actions([fixed])
    [entry] = ledger.entries()
    assert (entry.kind, entry.details) == ("user-action", "sudo gpasswd -d $USER libvirt")
    doctor.remember_user_actions([fixed])                  # recorded once
    assert len(ledger.entries()) == 1


def test_vagrant_up_is_retried_when_vagrant_gives_up_on_a_booting_vm(tmp_path, monkeypatch):
    """vagrant-libvirt's message is wrapped: "... a machine that is not\\nready for guest communication"."""
    from pathlib import Path

    from autorelabel import lab as lab_mod
    from autorelabel import proc
    from autorelabel.config import Settings

    lab = lab_mod.Lab(Settings(provider="libvirt", storage_dir=str(tmp_path)), "rhcsa")
    monkeypatch.setattr(lab, "guard_hypervisors", lambda: None)
    monkeypatch.setattr(lab_mod.ledger, "record", lambda *a, **k: None)
    monkeypatch.setattr(lab_mod.time, "sleep", lambda s: None)
    gave_up = ("==> utility: Removing domain...\nGuest-specific operations were attempted on a machine that is not\n"
               "ready for guest communication. This should not happen and a bug\nshould be reported.\n")
    answers = [proc.Result(["vagrant"], 1, gave_up, "", 15.0), proc.Result(["vagrant"], 0, "", "", 60.0)]
    calls, steps = [], []
    monkeypatch.setattr(lab, "vagrant", lambda args, **k: calls.append(args) or answers[len(calls) - 1])
    lab._vagrant_up(["utility"], steps.append, None, Path(tmp_path / "up.log"), None)
    assert len(calls) == 2 and any("retrying" in s for s in steps)


def test_the_socket_directory_must_be_this_users_own(tmp_path, monkeypatch):
    import os

    from autorelabel import paths

    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    d = paths.runtime_dir()
    assert d == tmp_path / "autorelabel" and oct(d.stat().st_mode & 0o777) == "0o700"

    d.chmod(0o755)                                   # ours, but open to others: closed again
    assert oct(paths.runtime_dir().stat().st_mode & 0o777) == "0o700"

    real_uid = os.getuid()
    monkeypatch.setattr(paths.os, "getuid", lambda: real_uid + 1)      # as if someone else had made it
    with pytest.raises(paths.UnsafeRuntimeDir, match="belongs to another user"):
        paths.runtime_dir()
    monkeypatch.setattr(paths.os, "getuid", lambda: real_uid)

    d.rmdir()
    d.symlink_to(tmp_path)                           # a link planted under the expected name
    with pytest.raises(paths.UnsafeRuntimeDir, match="not a directory"):
        paths.runtime_dir()


def test_every_pinned_wheel_has_its_hash():
    """The lock is the pins plus one sha256 each: pip refuses anything else (--require-hashes)."""
    import re

    from autorelabel import content

    pins = {ln.strip().lower() for ln in content.WHEEL_PINS.read_text().splitlines()
            if "==" in ln and not ln.startswith("#")}
    locked = content.locked_hashes()
    assert set(locked) == pins and len(pins) > 40
    assert all(re.fullmatch(r"[0-9a-f]{64}", h) for h in locked.values())
    assert len(set(locked.values())) == len(locked)


def test_a_wheel_that_is_not_the_recorded_file_is_found(tmp_path, monkeypatch):
    import hashlib

    from autorelabel import content

    good = tmp_path / "good-1.0-py3-none-any.whl"
    good.write_bytes(b"the real wheel")
    (tmp_path / "bad-1.0-py3-none-any.whl").write_bytes(b"something else")
    lock = tmp_path / "lock"
    lock.write_text(f"# comment\ngood==1.0 \\\n    --hash=sha256:{hashlib.sha256(b'the real wheel').hexdigest()}\n"
                    f"bad==1.0 \\\n    --hash=sha256:{'0' * 64}\n")
    monkeypatch.setattr(content, "WHEEL_LOCK", lock)
    assert content.locked_hashes()["good==1.0"] == hashlib.sha256(b"the real wheel").hexdigest()
    assert content.unexpected_wheels(tmp_path) == ["bad-1.0-py3-none-any.whl"]


def test_the_wheel_download_is_hash_checked(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from autorelabel import content, proc
    from autorelabel.config import Settings

    seen: list[list[str]] = []

    def stream(cmd, **kwargs):
        seen.append(cmd)
        return SimpleNamespace(ok=False)

    monkeypatch.setattr(proc, "stream", stream)
    with pytest.raises(content.ContentError):
        content.download(Settings(provider="libvirt", storage_dir=str(tmp_path)))
    cmd = seen[0]
    assert "--require-hashes" in cmd and "--no-deps" in cmd and "-c" not in cmd
    assert cmd[cmd.index("-r") + 1] == str(content.WHEEL_LOCK)


def test_the_control_node_installs_only_hash_checked_wheels():
    from autorelabel import paths

    script = (paths.VAGRANT_DIR / "provision" / "control.sh").read_text()
    install = script[script.index("/opt/ansible-navigator/bin/pip install"):].split("\nfi\n")[0]
    assert "--require-hashes" in install and "--no-deps" in install and "rhce-wheels.lock" in install
