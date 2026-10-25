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
