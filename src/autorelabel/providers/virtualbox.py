"""VirtualBox operations outside Vagrant, mirroring providers.libvirt's interface:
power, pause, snapshots, console, and moving VMs into the lab storage folder."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from .. import console_keeper, paths, proc


class VirtualBoxError(RuntimeError):
    pass


class ProfileBusy(VirtualBoxError):
    user_fixable = True
    hint = ("Close VirtualBox Manager and shut down your own VirtualBox VMs, then retry. VirtualBox "
            "serves one settings profile at a time, and autorelabel keeps its lab VMs out of yours.")


SERVICE_WAIT = 60   # an idle VBoxSVC exits about 5 s after its last client
PARAVIRT = "minimal"  # paravirtualization interface of the lab VMs (see start)


def service_homes(proc_root: Path = Path("/proc")) -> list[Path | None]:
    """The profile each running VBoxSVC of this user serves (None: the default profile)."""
    homes: list[Path | None] = []
    uid = os.getuid()
    for pid_dir in proc_root.iterdir():
        if not pid_dir.name.isdigit():
            continue
        try:
            if pid_dir.stat().st_uid != uid or (pid_dir / "comm").read_text().strip() != "VBoxSVC":
                continue
            environ = (pid_dir / "environ").read_bytes().split(b"\0")
        except OSError:
            continue
        home = next((e.split(b"=", 1)[1].decode() for e in environ if e.startswith(b"VBOX_USER_HOME=")), "")
        homes.append(Path(home).resolve() if home else None)
    return homes


def wait_for_own_service(home: Path, timeout: float = SERVICE_WAIT, proc_root: Path = Path("/proc")) -> None:
    """VirtualBox runs one VBoxSVC per user, and VBOX_USER_HOME only counts when it starts.
    While one serves another profile (VirtualBox Manager open, the user's own VMs running, or a
    command a moment ago), our VBoxManage calls would silently act on that profile: register lab
    VMs in the user's VM list, or change the user's default machine folder. Wait for it to exit;
    refuse if it stays."""
    want = home.resolve()
    deadline = time.monotonic() + timeout
    while any(h != want for h in service_homes(proc_root)):
        if time.monotonic() >= deadline:
            raise ProfileBusy("VirtualBox is busy with your own VirtualBox settings "
                              "(VirtualBox Manager or your own VMs are running)")
        time.sleep(1)


def vbm(*args: str, timeout: float = 120, check: bool = False) -> proc.Result:
    home = os.environ.get("VBOX_USER_HOME")
    if home:
        wait_for_own_service(Path(home))
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
    ensure_console_keeper()
    # Not KVM's paravirtual clock: with it, a Linux guest's clock at random jumps by centuries
    # right after the boot loader and the boot stalls. Set before every start, because reverting
    # a snapshot brings back the settings the snapshot was taken with.
    for _ in range(3):
        if vbm("modifyvm", name, "--paravirt-provider", PARAVIRT, timeout=30).ok:
            break
        time.sleep(1)          # the session of a VM that just stopped is still closing
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


def console_dir() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime) / "autorelabel" if runtime else Path(f"/tmp/autorelabel-{os.getuid()}")
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    return base


def console_socket(name: str) -> Path:
    return console_keeper.vm_socket(console_dir(), name)


def ensure_console_keeper(timeout: float = 6) -> None:
    """Start the console keeper unless it runs: a VM whose serial console nobody drains
    boots at a crawl (see console_keeper). Call before starting a VM."""
    sock = console_dir() / "keeper.sock"
    if console_keeper.alive(sock):
        return
    paths.LOGS.mkdir(parents=True, exist_ok=True)
    with open(paths.LOGS / "console-keeper.log", "ab") as log:
        subprocess.Popen([sys.executable, "-m", "autorelabel.console_keeper", str(console_dir())],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd="/",
                         start_new_session=True, close_fds=True)
    deadline = time.monotonic() + timeout
    while not console_keeper.alive(sock):
        if time.monotonic() > deadline:
            raise VirtualBoxError(f"the console keeper did not start; see {paths.LOGS / 'console-keeper.log'}")
        time.sleep(0.05)


def console_command(name: str) -> list[str]:
    ensure_console_keeper()
    return [sys.executable, "-m", "autorelabel.console_bridge", str(console_dir() / "keeper.sock"), name]


def move(name: str, folder: Path) -> proc.Result:
    """Relocate a powered-off VM (config and disks) into `folder`."""
    folder.mkdir(parents=True, exist_ok=True)
    return vbm("movevm", name, "--type", "basic", "--folder", str(folder), timeout=1800)


def remove_dhcp_server(ifname: str) -> bool:
    """VirtualBox gives a new host-only interface a DHCP server (192.168.56.x). The lab network has
    none, as on libvirt: a lab NIC switched to DHCP must get no address. True if one was removed."""
    res = vbm("list", "dhcpservers", timeout=30)
    nets = {line.split(":", 1)[1].strip() for line in res.out.splitlines() if line.startswith("NetworkName:")}
    net = f"HostInterfaceNetworking-{ifname}"
    return net in nets and vbm("dhcpserver", "remove", f"--network={net}", timeout=30).ok


def hostonly_interfaces() -> set[str]:
    res = vbm("list", "hostonlyifs", timeout=30)
    names = {line.split(":", 1)[1].strip() for line in res.out.splitlines() if line.startswith("Name:")}
    res2 = vbm("list", "hostonlynets", timeout=30)
    names |= {line.split(":", 1)[1].strip() for line in res2.out.splitlines() if line.startswith("Name:")}
    return names
