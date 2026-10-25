"""Build the autorelabel/rhel10 Vagrant box with Packer, offline from the ISO."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path

from . import hostinfo, ledger, log, paths, proc, vagrant
from .config import Settings
from .fsutil import atomic_write_json, disk_free_bytes, read_json

_log = log.get("box")
BUILD_MIN_FREE_GB = 25
PACKER_SOURCE = {"libvirt": "qemu.rhel10", "virtualbox": "virtualbox-iso.rhel10"}


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


def manifest_path(settings: Settings, provider: str) -> Path:
    return storage_layout(settings)["boxes"] / f"manifest-{provider}.json"


def manifest(settings: Settings, provider: str) -> dict | None:
    return read_json(manifest_path(settings, provider), default=None)


def box_status(settings: Settings, provider: str) -> tuple[bool, str]:
    """(usable, message). Usable means the box is added to Vagrant and matches the ISO."""
    box = vagrant.has_box(provider)
    if not box:
        return False, "not built yet"
    m = manifest(settings, provider)
    if not m:
        return True, f"{box.name} v{box.version} (no build manifest)"
    iso = Path(settings.iso_path)
    vol = hostinfo.iso_volume_id(iso) if iso.exists() else None
    if vol and m.get("iso_volume_id") and vol != m["iso_volume_id"]:
        return False, f"box was built from {m['iso_volume_id']} but the configured ISO is {vol}; rebuild"
    return True, f"RHEL {m.get('rhel_version', '?')} · built {m.get('built', '?')}"


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

    step("Installing RHEL from the ISO (about 10-15 minutes)")
    cmd = [
        "packer", "build", "-force", "-color=false", "-on-error=cleanup",
        f"-only={PACKER_SOURCE[provider]}",
        "-var", f"iso_path={iso}",
        "-var", f"iso_checksum=sha256:{digest}",
        "-var", f"output_dir={out_dir}",
        "-var", f"box_version={version}",
        "-var", f"volume_label={vol}",
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

    box_file = out_dir / f"autorelabel-rhel10-{'libvirt' if provider == 'libvirt' else 'virtualbox'}.box"
    if not box_file.exists():
        candidates = sorted(out_dir.glob("*.box"))
        if not candidates:
            raise BoxError("packer finished but produced no .box file", log_file=log_file)
        box_file = candidates[0]

    step("Adding the box to Vagrant")
    ledger.record("vagrant-box", vagrant.BOX_NAME, provider, storage_dir=settings.storage_dir)
    res = vagrant.box_add(box_file, provider, on_line=on_line, log_file=log_file)
    if not res.ok:
        raise BoxError("vagrant box add failed", log_file=log_file)

    atomic_write_json(manifest_path(settings, provider), {
        "box": vagrant.BOX_NAME,
        "provider": provider,
        "version": version,
        "rhel_version": rhel,
        "iso_volume_id": vol,
        "iso_sha256": digest,
        "built": time.strftime("%Y-%m-%d %H:%M"),
        "kickstart_sha256": hashlib.sha256((paths.PACKER_DIR / "http" / "ks.cfg.pkrtpl").read_bytes()).hexdigest(),
    })
    step("Cleaning up build files")
    shutil.rmtree(out_dir, ignore_errors=True)
    _log.info("box built for %s from %s", provider, json.dumps(vol))
    return log_file
