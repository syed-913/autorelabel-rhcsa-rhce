"""VirtualBox operations outside Vagrant, mirroring providers.libvirt's interface:
power, pause, snapshots, console, and moving VMs into the lab storage folder."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from .. import proc


class VirtualBoxError(RuntimeError):
    pass


def vbm(*args: str, timeout: float = 120, check: bool = False) -> proc.Result:
    res = proc.run(["VBoxManage", *args], timeout=timeout)
    if check and not res.ok:
        raise VirtualBoxError(f"VBoxManage {' '.join(args[:2])}: {res.tail(3)}")
    return res


def ensure_profile(home: Path, machine_folder: Path) -> None:
    """Create the private VirtualBox profile (VBOX_USER_HOME is already set for this process)
    and point its default machine folder into the lab storage directory."""
    home.mkdir(parents=True, exist_ok=True)
    machine_folder.mkdir(parents=True, exist_ok=True)
    env_home = os.environ.get("VBOX_USER_HOME", "")
    if Path(env_home or "/nonexistent").resolve() != home.resolve():
        raise VirtualBoxError(f"VBOX_USER_HOME is {env_home!r}, expected {home}")
    res = vbm("list", "systemproperties", timeout=60)
    current = next((ln.split(":", 1)[1].strip() for ln in res.out.splitlines()
                    if ln.startswith("Default machine folder:")), "")
    if current != str(machine_folder):
        vbm("setproperty", "machinefolder", str(machine_folder), check=True)


def _info(name: str) -> dict[str, str]:
    res = vbm("showvminfo", name, "--machinereadable", timeout=30)
    if not res.ok:
        return {}
    out = {}
    for line in res.out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip('"')] = v.strip('"')
    return out


def domain_exists(name: str) -> bool:
    return bool(_info(name))


_STATE = {"running": "running", "paused": "paused", "poweroff": "shut off", "aborted": "crashed",
          "saved": "shut off", "starting": "running", "stopping": "running", "restoring": "running"}


def state(name: str) -> tuple[str, str]:
    info = _info(name)
    if not info:
        return ("missing", "")
    raw = info.get("VMState", "")
    return (_STATE.get(raw, raw), raw)


def start(name: str) -> proc.Result:
    return vbm("startvm", name, "--type", "headless", timeout=180)


def shutdown(name: str, wait: float = 120) -> bool:
    vbm("controlvm", name, "acpipowerbutton", timeout=30)
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if state(name)[0] in ("shut off", "crashed"):
            return True
        time.sleep(2)
    return False


def destroy(name: str) -> proc.Result:
    """Hard power-off (like pulling the plug)."""
    return vbm("controlvm", name, "poweroff", timeout=60)


def reset(name: str) -> proc.Result:
    return vbm("controlvm", name, "reset", timeout=30)


def ctrl_alt_del(name: str) -> proc.Result:
    """systemd answers Ctrl+Alt+Del with a clean reboot, even in emergency mode (scan codes:
    Ctrl, Alt, Delete pressed, then released)."""
    return vbm("controlvm", name, "keyboardputscancode", "1d", "38", "e0", "53", "e0", "d3", "b8", "9d",
               timeout=15)


def reboot_acpi(name: str) -> proc.Result:
    """VirtualBox has no ACPI reboot: press the power button, then power on again."""
    if shutdown(name, wait=60):
        return start(name)
    return reset(name)


def suspend(name: str) -> proc.Result:
    return vbm("controlvm", name, "pause", timeout=30)


def resume(name: str) -> proc.Result:
    return vbm("controlvm", name, "resume", timeout=30)


def time_sync(name: str) -> proc.Result:
    """No guest agent without Guest Additions: the guest's chrony catches up on its own."""
    return proc.Result(["true"], 0, "", "", 0.0)


def snapshot_create(name: str, snap: str, description: str = "") -> proc.Result:
    args = ["snapshot", name, "take", snap]
    if description:
        args += ["--description", description]
    return vbm(*args, timeout=600)


def snapshot_revert(name: str, snap: str) -> proc.Result:
    if state(name)[0] not in ("shut off", "crashed", "missing"):
        destroy(name)
        time.sleep(2)
    return vbm("snapshot", name, "restore", snap, timeout=600)


def snapshot_delete(name: str, snap: str) -> proc.Result:
    return vbm("snapshot", name, "delete", snap, timeout=600)


def snapshots(name: str) -> list[str]:
    res = vbm("snapshot", name, "list", "--machinereadable", timeout=30)
    if not res.ok:
        return []
    out = []
    for line in res.out.splitlines():
        if line.startswith("SnapshotName"):
            out.append(line.split("=", 1)[1].strip('"'))
    return out


def console_socket(name: str) -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime) / "autorelabel" if runtime else Path(f"/tmp/autorelabel-{os.getuid()}")
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    return base / f"console-{name}.sock"


def console_command(name: str) -> list[str]:
    return [sys.executable, "-m", "autorelabel.console_bridge", str(console_socket(name))]


def move(name: str, folder: Path) -> proc.Result:
    """Relocate a powered-off VM (config and disks) into `folder`."""
    folder.mkdir(parents=True, exist_ok=True)
    return vbm("movevm", name, "--type", "basic", "--folder", str(folder), timeout=1800)


def hostonly_interfaces() -> set[str]:
    res = vbm("list", "hostonlyifs", timeout=30)
    names = {line.split(":", 1)[1].strip() for line in res.out.splitlines() if line.startswith("Name:")}
    res2 = vbm("list", "hostonlynets", timeout=30)
    names |= {line.split(":", 1)[1].strip() for line in res2.out.splitlines() if line.startswith("Name:")}
    return names
