"""The RHEL 10 box: built with Packer, offline from the ISO, and kept as autorelabel's own files
in the lab storage directory (boxes/<provider>/: the disk image or the OVF, the SSH key the box
trusts, and manifest-<provider>.json). Boxes earlier versions added to Vagrant are converted once."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path

from . import hostinfo, ledger, log, paths, proc, vagrant_legacy
from .config import Settings
from .fsutil import atomic_write_json, disk_free_bytes, read_json

_log = log.get("box")
BUILD_MIN_FREE_GB = 25
PACKER_SOURCE = {"libvirt": "qemu.rhel10", "virtualbox": "virtualbox-iso.rhel10"}
BOX_FORMAT = 2          # 1: a Vagrant box (up to 1.4); 2: autorelabel's own files
KEY = "ssh_key"         # the private key the box's vagrant account trusts (KEY + ".pub" next to it)
# SHA-256 of Red Hat's x86_64 DVD ISOs as published on https://developers.redhat.com/products/rhel/download
# (the Customer Portal lists the same). Add new minor releases here when Red Hat publishes them.
RED_HAT_DVD_SHA256 = {
    "edce2dd6f8e1d1b2ff0b204f89b0659bc9e320d175beb7caad60712957a19608": "10.0",
    "e15cb333529c332e76e4b1b946efe3515c99f996546675aec18e8effdf2540a5": "10.2",
}


class BoxError(RuntimeError):
    def __init__(self, message: str, hint: str = "", log_file: Path | None = None, user_fixable: bool = False):
        super().__init__(message)
        self.hint = hint
        self.log_file = log_file
        self.user_fixable = user_fixable   # the user's situation, not a failure: no problem report


def storage_layout(settings: Settings) -> dict[str, Path]:
    root = paths.storage_root(settings.storage_dir)
    return {
        "root": root,
        "pool": root / "libvirt-pool",
        "packer": root / "packer",
        "build": root / "packer" / "build",
        "boxes": root / "boxes",
        "content": root / "content",
        "vbox_home": paths.vbox_home(settings.storage_dir),
        "vbox_vms": root / "virtualbox" / "vms",
        "vbox_disks": root / "virtualbox" / "disks",
    }


def ensure_storage(settings: Settings) -> dict[str, Path]:
    """Create our storage subdirectory (ledgered first) and the rescue kit."""
    layout = storage_layout(settings)
    root = layout["root"]
    ledger.record("dir", str(root), "lab storage", storage_dir=settings.storage_dir)
    for key in ("root", "packer", "boxes", "content"):
        layout[key].mkdir(parents=True, exist_ok=True)
    ledger.install_rescue_kit(settings.storage_dir)
    return layout


def iso_sha256(iso: Path, on_progress: Callable[[float], None] | None = None) -> str:
    """sha256 of the ISO, cached by (path, size, mtime) so it is computed once."""
    cache_file = paths.WORKSPACE / "iso-checksums.json"
    cache = read_json(cache_file, default={}) or {}
    st = iso.stat()
    key = f"{iso.resolve()}|{st.st_size}|{int(st.st_mtime)}"
    if key in cache:
        return cache[key]
    h = hashlib.sha256()
    done = 0
    with open(iso, "rb") as fh:
        while chunk := fh.read(8 * 1024 * 1024):
            h.update(chunk)
            done += len(chunk)
            if on_progress:
                on_progress(done / st.st_size)
    digest = h.hexdigest()
    cache[key] = digest
    atomic_write_json(cache_file, cache)
    return digest


def check_iso(digest: str, rhel: str) -> tuple[bool | None, str]:
    """(verified, message). True: the ISO is exactly what Red Hat published. False: Red Hat published a
    different checksum for this RHEL version, so the download is damaged or altered. None: no published
    checksum is known for this version (a newer release, or one only on the Customer Portal)."""
    if digest in RED_HAT_DVD_SHA256:
        return True, f"The ISO matches Red Hat's published checksum for the RHEL {RED_HAT_DVD_SHA256[digest]} DVD."
    if rhel in RED_HAT_DVD_SHA256.values():
        return False, f"The ISO doesn't match Red Hat's published checksum for the RHEL {rhel} DVD."
    return None, (f"autorelabel doesn't know Red Hat's checksum for the RHEL {rhel} DVD yet. To check the ISO "
                  f"yourself, compare its SHA-256 with the one on Red Hat's download page: {digest}")


def manifest_path(settings: Settings, provider: str) -> Path:
    return storage_layout(settings)["boxes"] / f"manifest-{provider}.json"


def manifest(settings: Settings, provider: str) -> dict | None:
    return read_json(manifest_path(settings, provider), default=None)


def box_dir(settings: Settings, provider: str) -> Path:
    return storage_layout(settings)["boxes"] / provider


def key_path(settings: Settings, provider: str) -> Path:
    return box_dir(settings, provider) / KEY


def image(settings: Settings, provider: str) -> Path:
    """libvirt: the qcow2 disk. VirtualBox: the OVF (its disk sits next to it)."""
    m = manifest(settings, provider) or {}
    return box_dir(settings, provider) / m.get("image", "rhel10.qcow2" if provider == "libvirt" else "rhel10.ovf")


def installed(settings: Settings, provider: str) -> bool:
    m = manifest(settings, provider) or {}
    return (m.get("format") == BOX_FORMAT and image(settings, provider).is_file()
            and key_path(settings, provider).is_file())


def box_status(settings: Settings, provider: str) -> tuple[bool, str]:
    """(usable, message). Usable: the box is installed (or an earlier version's Vagrant box can be
    converted) and matches the configured ISO."""
    m = manifest(settings, provider)
    if not installed(settings, provider):
        old = vagrant_legacy.find_box(provider)
        if not old:
            return False, "not built yet"
        return True, f"box from an earlier version (Vagrant, v{old.version}); converted on first use"
    iso = Path(settings.iso_path)
    vol = hostinfo.iso_volume_id(iso) if iso.exists() else None
    if m and vol and m.get("iso_volume_id") and vol != m["iso_volume_id"]:
        return False, f"box was built from {m['iso_volume_id']} but the configured ISO is {vol}; rebuild"
    m = m or {}
    verified = " · ISO verified" if m.get("iso_verified") else ""
    return True, f"RHEL {m.get('rhel_version', '?')} · built {m.get('built', '?')}{verified}"


def ensure_installed(settings: Settings, provider: str, step: Callable[[str], None] | None = None) -> dict:
    """The box's manifest, converting an earlier version's Vagrant box first if that is all there is."""
    if not installed(settings, provider):
        old = vagrant_legacy.find_box(provider)
        if not old:
            raise BoxError("the RHEL 10 box is not built yet", "Build the box first (Lab → Build box).",
                           user_fixable=True)
        if step:
            step("Converting the box from an earlier version (once)")
        try:
            convert(settings, provider, old)
        except OSError as exc:
            raise BoxError(f"could not convert the box from an earlier version: {exc}",
                           "Build the box again (Lab → Build box).") from exc
    return manifest(settings, provider) or {}


def convert(settings: Settings, provider: str, old: vagrant_legacy.OldBox) -> None:
    """Copy an earlier version's Vagrant box into boxes/<provider>/ with the key it trusts (Vagrant's
    well-known one: each lab replaces it with its own on first boot), then let Vagrant forget it."""
    dest = box_dir(settings, provider)
    tmp = dest.with_name(dest.name + ".converting")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    names = old.files()
    for src, name in names.items():
        shutil.copyfile(src, tmp / name)
    shutil.copyfile(old.key, tmp / KEY)
    (tmp / KEY).chmod(0o600)
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    m = manifest(settings, provider) or {"rhel_version": "?", "built": old.version}
    m.update({"format": BOX_FORMAT, "provider": provider, "version": m.get("version") or old.version,
              "image": "rhel10.qcow2" if provider == "libvirt" else "rhel10.ovf",
              "converted_from": f"vagrant {old.version}"})
    atomic_write_json(manifest_path(settings, provider), m)
    _log.info("converted the %s Vagrant box v%s into %s", provider, old.version, dest)
    vagrant_legacy.forget_box(provider)


def _install_build(settings: Settings, provider: str, out_dir: Path, new_key: Path) -> str:
    """Move Packer's output and the build's key into boxes/<provider>/. Returns the image's name."""
    dest = box_dir(settings, provider)
    tmp = dest.with_name(dest.name + ".new")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    if provider == "libvirt":
        src = out_dir / "qemu" / "box.img"
        if not src.is_file():
            raise BoxError("packer finished but produced no disk image")
        src.rename(tmp / "rhel10.qcow2")
        name = "rhel10.qcow2"
    else:
        ovfs = sorted((out_dir / "virtualbox").glob("*.ovf"))
        if not ovfs:
            raise BoxError("packer finished but produced no OVF")
        for f in (out_dir / "virtualbox").iterdir():
            f.rename(tmp / f.name)
        name = ovfs[0].name
    new_key.rename(tmp / KEY)
    new_key.with_name(new_key.name + ".pub").rename(tmp / (KEY + ".pub"))
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    return name


def build(
    settings: Settings,
    provider: str,
    *,
    on_line: Callable[[str], None] | None = None,
    on_step: Callable[[str], None] | None = None,
    cancel: threading.Event | None = None,
) -> Path:
    """Run the full build. Returns the log file path. Raises BoxError with a hint."""
    log_file = log.operation_log(f"box-build-{provider}")
    step = on_step or (lambda s: None)
    iso = Path(settings.iso_path).expanduser()
    if not iso.is_file():
        raise BoxError(f"ISO not found: {iso}", "Choose the RHEL 10 DVD ISO in Settings.", log_file, True)
    vol = hostinfo.iso_volume_id(iso)
    rhel = hostinfo.rhel_version_from_iso(vol)
    if not rhel or not rhel.startswith("10."):
        raise BoxError(f"{iso.name} is not a RHEL 10 DVD ISO", "Download the RHEL 10 'Binary DVD' ISO.", log_file,
                       True)

    layout = ensure_storage(settings)
    free_gb = disk_free_bytes(layout["root"]) / 1e9
    if free_gb < BUILD_MIN_FREE_GB:
        raise BoxError(f"only {free_gb:.0f} GB free in {layout['root']}",
                       f"The build needs about {BUILD_MIN_FREE_GB} GB free.", log_file, True)

    env = paths.tool_env(settings.storage_dir)
    if os.environ.get("AUTORELABEL_DEBUG"):
        env["PACKER_LOG"] = "1"
    for key in ("PACKER_CACHE_DIR", "PACKER_PLUGIN_PATH", "PACKER_CONFIG_DIR"):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    if provider == "virtualbox":
        from .providers import virtualbox as vb

        vb.ensure_profile(layout["vbox_home"], layout["vbox_vms"])

    step("Verifying the ISO checksum")
    last = [0.0]

    def progress(frac: float) -> None:
        if frac - last[0] >= 0.01:
            last[0] = frac
            if on_line:
                on_line(proc.Progress(f"Checksum: {frac * 100:.0f}%"))

    digest = iso_sha256(iso, progress)
    verified, message = check_iso(digest, rhel)
    _log.info("%s (sha256 %s)", message, digest)
    if on_line:
        on_line(message)
    if verified is False and not os.environ.get("AUTORELABEL_SKIP_ISO_CHECK"):
        raise BoxError(message.rstrip("."),
                       "The download is probably incomplete or damaged: download the ISO again from Red Hat. If "
                       "Red Hat's download page shows this exact checksum, the ISO was re-issued: please report "
                       "it, and build anyway with AUTORELABEL_SKIP_ISO_CHECK=1 ./autorelabel box build.",
                       log_file, True)

    step("Installing Packer plugins")
    res = proc.stream(["packer", "init", str(paths.PACKER_DIR)], env=env, cwd=paths.PACKER_DIR,
                      on_line=on_line, log_file=log_file, cancel=cancel, timeout=900)
    if res.cancelled:
        raise BoxError("cancelled", log_file=log_file, user_fixable=True)
    if not res.ok:
        raise BoxError("packer init failed", "Packer downloads its plugins once; check your internet connection.",
                       log_file)

    out_dir = layout["build"] / provider
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    version = time.strftime("%Y%m%d.%H%M")
    # The key the box's vagrant account trusts: made here, so no box carries a key known to others.
    key = out_dir / KEY
    res = proc.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "autorelabel-box", "-f", str(key)],
                   timeout=30)
    if not res.ok:
        raise BoxError(f"ssh-keygen failed: {res.tail(3)}", log_file=log_file)

    step("Installing RHEL from the ISO (about 10-15 minutes)")
    cmd = [
        "packer", "build", "-force", "-color=false", "-on-error=cleanup",
        f"-only={PACKER_SOURCE[provider]}",
        "-var", f"iso_path={iso}",
        "-var", f"iso_checksum=sha256:{digest}",
        "-var", f"output_dir={out_dir}",
        "-var", f"box_version={version}",
        "-var", f"volume_label={vol}",
        "-var", f"ssh_public_key={key.with_name(KEY + '.pub').read_text().strip()}",
        # RHEL-family hosts: only /usr/libexec/qemu-kvm, which has q35 machines but no i440fx ("pc")
        *(["-var", f"qemu_binary={hostinfo.RHEL_QEMU}", "-var", "machine_type=q35"]
          if provider == "libvirt" and hostinfo.qemu_system() == hostinfo.RHEL_QEMU else []),
        str(paths.PACKER_DIR),
    ]

    def packer_line(line: str) -> None:
        if "STEP:" in line:
            step(line.split("STEP:", 1)[1].strip().capitalize())
        if on_line:
            on_line(line)

    res = proc.stream(cmd, env=env, cwd=paths.PACKER_DIR, on_line=packer_line, log_file=log_file,
                      cancel=cancel, timeout=3 * 3600)
    if res.cancelled:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise BoxError("cancelled", log_file=log_file, user_fixable=True)
    if not res.ok:
        hint = "See the build log. If the installer never started, check the serial log in the build directory."
        if "Timeout waiting for SSH" in res.out:
            hint = "The installer did not finish in time. Check the serial log in the build directory."
        raise BoxError("packer build failed", hint, log_file)

    step("Installing the box")
    try:
        name = _install_build(settings, provider, out_dir, key)
    except BoxError as exc:
        exc.log_file = log_file
        raise
    atomic_write_json(manifest_path(settings, provider), {
        "format": BOX_FORMAT,
        "provider": provider,
        "version": version,
        "image": name,
        "rhel_version": rhel,
        "iso_volume_id": vol,
        "iso_sha256": digest,
        "iso_verified": verified,
        "built": time.strftime("%Y-%m-%d %H:%M"),
        "kickstart_sha256": hashlib.sha256((paths.PACKER_DIR / "http" / "ks.cfg.pkrtpl").read_bytes()).hexdigest(),
    })
    step("Cleaning up build files")
    shutil.rmtree(out_dir, ignore_errors=True)
    _log.info("box built for %s from %s", provider, json.dumps(vol))
    return log_file
