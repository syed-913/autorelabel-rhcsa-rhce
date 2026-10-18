"""Thin wrapper around the vagrant CLI. Always parses --machine-readable output."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import paths, proc

BOX_NAME = "autorelabel/rhel10"


def _env(storage_dir: str | None = None, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for project commands (up, status, ssh-config...)."""
    env = paths.tool_env(storage_dir)
    env["VAGRANT_CWD"] = str(paths.VAGRANT_DIR)
    if extra:
        env.update(extra)
    if env.get("VAGRANT_DEFAULT_PROVIDER") == "virtualbox" and env.get("VBOX_USER_HOME"):
        from .providers import virtualbox as vb

        vb.wait_for_own_service(Path(env["VBOX_USER_HOME"]))   # Vagrant runs VBoxManage itself
    return env


def _global_env() -> dict[str, str]:
    """Environment for global commands (plugin/box listing): no Vagrantfile is
    loaded, so they work before the lab is configured."""
    paths.ensure_workspace()
    env = paths.tool_env()
    env.pop("VAGRANT_CWD", None)
    return env


def _global(args: list[str], timeout: float = 90) -> proc.Result:
    return proc.run(["vagrant", *args], env=_global_env(), cwd=paths.TMP, timeout=timeout)


def _unescape(field: str) -> str:
    return field.replace("%!(VAGRANT_COMMA)", ",").replace("\\n", "\n").replace("\\r", "")


def parse_machine_readable(text: str) -> list[tuple[str, str, list[str]]]:
    """Return (target, type, data-fields) for each machine-readable line."""
    rows = []
    for line in text.splitlines():
        parts = line.split(",")
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        rows.append((parts[1], parts[2], [_unescape(p) for p in parts[3:]]))
    return rows


def plugins() -> dict[str, str]:
    res = _global(["plugin", "list", "--machine-readable"])
    out: dict[str, str] = {}
    current = None
    for target, typ, data in parse_machine_readable(res.out):
        if typ == "plugin-name" and data:
            current = data[0]
            out[current] = ""
        elif typ == "plugin-version" and data:
            out[target or current or ""] = data[0].split(",")[0].strip()
    return out


@dataclass(frozen=True)
class Box:
    name: str
    provider: str
    version: str


def boxes() -> list[Box]:
    res = _global(["box", "list", "--machine-readable"])
    out: list[Box] = []
    name = provider = version = None
    for _target, typ, data in parse_machine_readable(res.out):
        if typ == "box-name":
            name = data[0] if data else None
        elif typ == "box-provider":
            provider = data[0] if data else None
        elif typ == "box-version":
            version = data[0] if data else "0"
            if name and provider:
                out.append(Box(name, provider, version))
            name = provider = version = None
    return out


def has_box(provider: str) -> Box | None:
    for b in boxes():
        if b.name == BOX_NAME and b.provider == provider:
            return b
    return None


def box_add(box_file: Path, provider: str, *, on_line: Callable[[str], None] | None = None,
            log_file: Path | None = None) -> proc.Result:
    return proc.stream(
        ["vagrant", "box", "add", "--force", "--name", BOX_NAME, "--provider", provider, str(box_file)],
        env=_global_env(), cwd=paths.TMP, on_line=on_line, log_file=log_file, timeout=1800,
    )


def box_remove_all() -> proc.Result:
    return _global(["box", "remove", "--force", "--all", BOX_NAME], timeout=300)


def status(storage_dir: str | None, env_extra: dict[str, str]) -> dict[str, str]:
    res = proc.run(["vagrant", "status", "--machine-readable"], env=_env(storage_dir, env_extra), timeout=120)
    return {target: data[0] for target, typ, data in parse_machine_readable(res.out)
            if typ == "state" and target and data}


def run_stream(args: list[str], storage_dir: str | None, env_extra: dict[str, str], *,
               on_line: Callable[[str], None] | None = None, log_file: Path | None = None,
               cancel: threading.Event | None = None, timeout: float | None = None) -> proc.Result:
    env = _env(storage_dir, env_extra)
    if args[:1] in (["up"], ["reload"]) and env.get("VAGRANT_DEFAULT_PROVIDER") == "virtualbox":
        from .providers import virtualbox as vb

        vb.ensure_console_keeper()   # the VMs it boots need their serial consoles drained
    return proc.stream(["vagrant", *args], env=env, on_line=on_line,
                       log_file=log_file, cancel=cancel, timeout=timeout)


def ssh_config(machine: str, storage_dir: str | None, env_extra: dict[str, str]) -> dict[str, str]:
    res = proc.run(["vagrant", "ssh-config", machine], env=_env(storage_dir, env_extra), timeout=120)
    cfg: dict[str, str] = {}
    for line in res.out.splitlines():
        line = line.strip()
        if " " in line:
            k, v = line.split(None, 1)
            cfg.setdefault(k, v.strip('"'))
    return cfg
