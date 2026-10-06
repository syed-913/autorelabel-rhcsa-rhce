"""Write-ahead ledger of every host-side artifact autorelabel creates.

Each entry is recorded *before* the artifact is created, so a crash can never
leave something on the host that uninstall doesn't know about. The format is a
plain TSV so scripts/uninstall.sh (pure bash) can read it without Python:

    <unix-ts> \t <kind> \t <identifier> \t <details>

A mirror copy lives in the lab storage directory together with a copy of the
uninstaller, so cleanup still works if the repository folder was deleted first.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from . import paths
from .fsutil import append_line

KINDS = (
    "dir",               # a directory we created (removed recursively)
    "libvirt-pool",
    "libvirt-network",
    "libvirt-domain",
    "vagrant-box",
    "vbox-vm",
    "vbox-hostonly",
    "vbox-medium",
    "systemd-unit",
    "user-action",       # something the user ran with sudo; uninstall prints the undo
)


@dataclass(frozen=True)
class Entry:
    ts: int
    kind: str
    ident: str
    details: str


def _clean(field: str) -> str:
    return " ".join(str(field).replace("\t", " ").splitlines()).strip()


def _mirror_path(storage_dir: str | None) -> Path | None:
    if not storage_dir:
        return None
    return paths.storage_root(storage_dir) / "ledger.tsv"


def record(kind: str, ident: str, details: str = "", storage_dir: str | None = None) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown ledger kind: {kind}")
    if any(e.kind == kind and e.ident == ident for e in entries()):
        return
    line = "\t".join([str(int(time.time())), kind, _clean(ident), _clean(details)])
    append_line(paths.LEDGER_FILE, line)
    mirror = _mirror_path(storage_dir)
    if mirror and mirror.parent.exists():
        append_line(mirror, line)


def entries(path: Path | None = None) -> list[Entry]:
    path = path or paths.LEDGER_FILE
    out: list[Entry] = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return out
    for raw in text.splitlines():
        parts = raw.split("\t")
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        out.append(Entry(int(parts[0]), parts[1], parts[2], parts[3] if len(parts) > 3 else ""))
    return out


def install_rescue_kit(storage_dir: str) -> None:
    """Copy the uninstaller and the full ledger next to the lab data."""
    root = paths.storage_root(storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    src = paths.SCRIPTS / "uninstall.sh"
    if src.exists():
        dst = root / "uninstall.sh"
        shutil.copy2(src, dst)
        dst.chmod(0o755)
    if paths.LEDGER_FILE.exists():
        shutil.copy2(paths.LEDGER_FILE, root / "ledger.tsv")
