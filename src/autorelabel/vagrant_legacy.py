"""What versions up to 1.4 left in Vagrant: the box, and the SSH keys of labs Vagrant made.

autorelabel no longer needs Vagrant. This module only reads Vagrant's files, so a box built
earlier is converted (box.convert) and a lab Vagrant made keeps working, even after Vagrant is
uninstalled. Vagrant itself is run once, if it is installed: to forget a box after converting it.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from . import log, paths, proc

_log = log.get("vagrant_legacy")
BOX_NAME = "autorelabel/rhel10"


def vagrant_home() -> Path:
    return Path(os.environ.get("VAGRANT_HOME") or Path.home() / ".vagrant.d")


def _version_key(v: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in v.split("."))


@dataclass(frozen=True)
class OldBox:
    provider: str
    version: str
    folder: Path      # the provider folder of that box version
    key: Path         # the private key the box trusts (Vagrant's well-known key)

    def files(self) -> dict[Path, str]:
        """Source file -> name in boxes/<provider>/."""
        if self.provider == "libvirt":
            meta = json.loads((self.folder / "metadata.json").read_text())
            disks = meta.get("disks") or [{"path": "box.img"}]
            return {self.folder / disks[0]["path"]: "rhel10.qcow2"}
        out = {}
        for f in sorted(self.folder.iterdir()):
            if f.suffix == ".ovf":
                out[f] = "rhel10.ovf"
            elif f.suffix == ".vmdk":
                out[f] = f.name      # the OVF names its disk
        return out


def find_box(provider: str) -> OldBox | None:
    """The newest autorelabel/rhel10 box for `provider` in Vagrant's box folder, or None."""
    root = vagrant_home() / "boxes" / BOX_NAME.replace("/", "-VAGRANTSLASH-")
    key = vagrant_home() / "insecure_private_keys" / "vagrant.key.ed25519"
    if not key.is_file():
        key = vagrant_home() / "insecure_private_key"
    if not root.is_dir() or not key.is_file():
        return None
    for version in sorted((d.name for d in root.iterdir() if d.is_dir()), key=_version_key, reverse=True):
        # Vagrant 2.4 adds an architecture level for boxes that name one
        for folder in (root / version / provider, *sorted((root / version).glob(f"*/{provider}"))):
            if (folder / "metadata.json").is_file():
                box = OldBox(provider, version, folder, key)
                try:
                    if box.files() and all(f.is_file() for f in box.files()):
                        return box
                except (OSError, ValueError, KeyError, IndexError):
                    _log.warning("unreadable Vagrant box in %s", folder)
    return None


def forget_box(provider: str) -> None:
    """After converting: remove the box from Vagrant (frees its copy), if Vagrant is installed."""
    if not proc.which("vagrant"):
        return
    res = proc.run(["vagrant", "box", "remove", "--force", "--all", "--provider", provider, BOX_NAME],
                   env=paths.tool_env(), cwd=paths.TMP, timeout=300)
    if not res.ok:
        _log.warning("vagrant box remove %s: %s", provider, res.tail(3))


def machine_key(exam: str, name: str, provider: str) -> Path:
    """The key Vagrant put into a lab VM it made (the lab replaced Vagrant's well-known key)."""
    return paths.VAGRANT_DOTFILE / exam / "machines" / name / provider / "private_key"
