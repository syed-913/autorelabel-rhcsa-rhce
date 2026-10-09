"""Well-known locations. Everything mutable lives under .workspace/ (repo) or the
lab storage directory chosen by the user; nothing is written elsewhere."""

from __future__ import annotations

import os
from pathlib import Path

PREFIX = "autorelabel"


def repo_root() -> Path:
    env = os.environ.get("AUTORELABEL_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


ROOT = repo_root()
# AUTORELABEL_WORKSPACE keeps a second, fully separate setup (e.g. another provider) side by side.
WORKSPACE = Path(os.environ.get("AUTORELABEL_WORKSPACE") or ROOT / ".workspace").resolve()
LOGS = WORKSPACE / "logs"
SESSIONS = WORKSPACE / "sessions"
TMP = WORKSPACE / "tmp"
VAGRANT_DOTFILE = WORKSPACE / "vagrant"
CONFIG_FILE = WORKSPACE / "config.json"
LEDGER_FILE = WORKSPACE / "ledger.tsv"
HISTORY_FILE = WORKSPACE / "history.jsonl"
KNOWN_HOSTS = WORKSPACE / "known_hosts"

BANKS = ROOT / "banks"
VAGRANT_DIR = ROOT / "vagrant"
PACKER_DIR = ROOT / "packer"
SCRIPTS = ROOT / "scripts"
DATA = Path(__file__).resolve().parent / "data"


def ensure_workspace() -> None:
    for d in (WORKSPACE, LOGS, SESSIONS, TMP, VAGRANT_DOTFILE):
        d.mkdir(parents=True, exist_ok=True)


def storage_root(storage_dir: str | os.PathLike[str]) -> Path:
    """The only directory we ever write to inside the user's chosen location."""
    return Path(storage_dir).expanduser().resolve() / PREFIX


def vbox_home(storage_dir: str | os.PathLike[str]) -> Path:
    """autorelabel's private VirtualBox profile (VBOX_USER_HOME): our VMs never appear in,
    or depend on, the user's own VirtualBox VM list and settings."""
    return storage_root(storage_dir) / "virtualbox" / "profile"


def tool_env(storage_dir: str | None = None) -> dict[str, str]:
    """Environment for child tools (vagrant, packer, pip): keeps their state in our
    directories and disables phone-home checks, so $HOME stays clean."""
    env = dict(os.environ)
    env.update(
        {
            "VAGRANT_DOTFILE_PATH": str(VAGRANT_DOTFILE),
            "VAGRANT_CHECKPOINT_DISABLE": "1",
            "VAGRANT_NO_COLOR": "1",
            "CHECKPOINT_DISABLE": "1",
            "PIP_NO_CACHE_DIR": "1",
            "TMPDIR": str(TMP),
        }
    )
    if storage_dir:
        root = storage_root(storage_dir)
        env["PACKER_CACHE_DIR"] = str(root / "packer" / "cache")
        env["PACKER_PLUGIN_PATH"] = str(root / "packer" / "plugins")
        env["PACKER_CONFIG_DIR"] = str(root / "packer" / "config")
        env["VBOX_USER_HOME"] = str(vbox_home(storage_dir))
    return env
