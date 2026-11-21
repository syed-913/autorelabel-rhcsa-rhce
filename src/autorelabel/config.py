"""User settings, persisted in .workspace/config.json."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import paths
from .fsutil import atomic_write_json, read_json

PROVIDERS = ("libvirt", "virtualbox")
PROFILES = ("lite", "standard")
SCORING = ("partial", "strict")


@dataclass
class Settings:
    provider: str = ""                # "" until chosen in the wizard
    profile: str = "lite"
    storage_dir: str = ""             # user-chosen parent; we only write to <storage_dir>/autorelabel
    iso_path: str = ""
    scoring: str = "partial"
    show_difficulty_during_exam: bool = False
    warnings_minutes: list[int] = field(default_factory=lambda: [30, 10, 5, 1])
    mgmt_subnet: str = "192.168.250.0/24"
    lab_subnet_libvirt: str = "172.25.250.0/24"
    lab_subnet_virtualbox: str = "192.168.60.0/24"
    code_server: bool = True
    forgive_downtime: bool = True

    @property
    def configured(self) -> bool:
        return bool(self.provider and self.storage_dir and self.iso_path)

    @property
    def lab_subnet(self) -> str:
        return self.lab_subnet_virtualbox if self.provider == "virtualbox" else self.lab_subnet_libvirt

    def validate(self) -> list[str]:
        problems = []
        if self.provider and self.provider not in PROVIDERS:
            problems.append(f"unknown provider {self.provider!r}")
        if self.profile not in PROFILES:
            problems.append(f"unknown profile {self.profile!r}")
        if self.scoring not in SCORING:
            problems.append(f"unknown scoring mode {self.scoring!r}")
        return problems


def default_storage_dir() -> Path:
    """The suggested lab storage parent: the XDG data directory, so the lab goes into
    ~/.local/share/autorelabel unless you pick another disk (home if that doesn't exist)."""
    xdg = os.environ.get("XDG_DATA_HOME", "")
    data = Path(xdg) if os.path.isabs(xdg) else Path.home() / ".local" / "share"
    return data if data.is_dir() else Path.home()


def storage_problem(value: str) -> str:
    """Why `value` can't be the lab storage directory, or "" when it can. autorelabel writes only to
    <value>/autorelabel, and the uninstaller removes that folder, so it must be a folder of its own:
    never the repository (whose launcher is itself called `autorelabel`) or anything inside it."""
    if not value.strip():
        return "choose a directory"
    p = Path(value).expanduser()
    if not p.is_absolute():
        return "give the full path, starting with / or ~"
    if not p.is_dir():
        return "directory does not exist"
    p = p.resolve()
    root = paths.ROOT.resolve()
    if p == root or root in p.parents:
        return "that is autorelabel's own folder; choose a directory outside it"
    target = p / paths.PREFIX
    if target.exists() and (target.is_symlink() or not target.is_dir()):
        return f"{target} already exists and is not autorelabel's folder"
    if p in (Path("/"), Path("/home")):
        return "choose a directory of your own, such as your home folder or a data disk"
    return ""


def storage_in_use(storage_dir: str) -> bool:
    """True when autorelabel keeps a box, lab disks or a VirtualBox profile under this storage
    directory: moving it then would strand them (and libvirt's pool still points there)."""
    if not storage_dir:
        return False
    root = paths.storage_root(storage_dir)
    return any((root / sub).is_dir() and any((root / sub).iterdir())
               for sub in ("boxes", "libvirt-pool", "virtualbox"))


def _apply_env(settings: Settings) -> None:
    # Every VBoxManage / vagrant / packer we start uses the private VirtualBox profile.
    if settings.storage_dir:
        os.environ["VBOX_USER_HOME"] = str(paths.vbox_home(settings.storage_dir))


def load() -> Settings:
    raw = read_json(paths.CONFIG_FILE, default={}) or {}
    known = {f.name for f in fields(Settings)}
    settings = Settings(**{k: v for k, v in raw.items() if k in known})
    _apply_env(settings)
    return settings


def save(settings: Settings) -> None:
    paths.ensure_workspace()
    atomic_write_json(paths.CONFIG_FILE, asdict(settings))
    _apply_env(settings)
