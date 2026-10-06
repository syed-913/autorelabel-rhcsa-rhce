"""Lab lifecycle: host prerequisites (pool, networks), ordered bring-up,
provisioning over SSH, verification reboots, snapshots, power and teardown."""

from __future__ import annotations

import ipaddress
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import box, labfacts, labspec, ledger, log, paths, remote, vagrant
from .config import Settings
from .fsutil import atomic_write_json, read_json
from .providers import libvirt as lv

_log = log.get("lab")
EXAM_IDS = {"rhcsa": 1, "rhce": 2}
MGMT_NETWORK = "autorelabel-mgmt"
LAB_NETWORK = "autorelabel-lab"
POOL = "autorelabel"
STATE_FILE = paths.WORKSPACE / "lab.json"


class LabError(RuntimeError):
    def __init__(self, message: str, hint: str = "", log_file: Path | None = None):
        super().__init__(message)
        self.hint = hint
        self.log_file = log_file


@dataclass(frozen=True)
class LabVM:
    spec: labspec.VM
    mgmt_ip: str
    lab_ip: str
    lab_ip6: str
    mgmt_mac: str
    lab_mac: str
    domain: str

    @property
    def name(self) -> str:
        return self.spec.name


StepFn = Callable[[str], None]
LineFn = Callable[[str], None]


class Lab:
    def __init__(self, settings: Settings, exam: str):
        if exam not in labspec.EXAMS:
            raise ValueError(exam)
        self.settings = settings
        self.exam = exam
        self.provider = settings.provider
        self.prefix = f"autorelabel-{exam}-"
        self.env_file = paths.WORKSPACE / f"env-{exam}.json"
        self.dotfile = paths.VAGRANT_DOTFILE / exam
        mgmt = ipaddress.IPv4Network(settings.mgmt_subnet)
        labnet = ipaddress.IPv4Network(settings.lab_subnet)
        facts = labfacts.build(exam, settings.profile, self.provider, settings.lab_subnet, settings.mgmt_subnet)
        xid = EXAM_IDS[exam]
        self.vms: list[LabVM] = []
        for vm in labspec.topology(exam, settings.profile):
            o = vm.host_octet
            self.vms.append(LabVM(
                spec=vm,
                mgmt_ip=str(mgmt.network_address + o),
                lab_ip=str(labnet.network_address + o),
                lab_ip6=facts[vm.name]["ipv6"],
                mgmt_mac=f"52:54:00:fa:{xid:02x}:{o:02x}",
                lab_mac=f"52:54:00:fb:{xid:02x}:{o:02x}",
                domain=f"{self.prefix}{vm.name}",
            ))
        self.ipv6_prefix = facts["ipv6_prefix"]

    # --- helpers --------------------------------------------------------------------------
    def vm(self, name: str) -> LabVM:
        for v in self.vms:
            if v.name == name:
                return v
        raise KeyError(name)

    def names(self, role: str | None = None) -> list[str]:
        return [v.name for v in self.vms if role is None or v.spec.role == role]

    def env_extra(self) -> dict[str, str]:
        return {"AUTORELABEL_ENV": str(self.env_file), "VAGRANT_DOTFILE_PATH": str(self.dotfile),
                "VAGRANT_DEFAULT_PROVIDER": self.provider}

    def target(self, name: str) -> remote.Target:
        key = self.dotfile / "machines" / name / self.provider / "private_key"
        if not key.exists():
            key = Path.home() / ".vagrant.d" / "insecure_private_keys" / "vagrant.key.ed25519"
        return remote.Target(name=f"{self.exam}-{name}", host=self.vm(name).mgmt_ip, key=key)

    def state(self) -> dict[str, Any]:
        return read_json(STATE_FILE, default={}) or {}

    def save_state(self, **updates: Any) -> None:
        st = self.state()
        st.update(updates)
        atomic_write_json(STATE_FILE, st)

    # --- host prerequisites -------------------------------------------------------------
    def prepare_host(self) -> None:
        layout = box.ensure_storage(self.settings)
        if self.provider != "libvirt":
            raise LabError("VirtualBox labs arrive in a later milestone; use the libvirt provider for now.")
        sd = self.settings.storage_dir
        lv.ensure_pool(POOL, layout["pool"], sd)
        lv.ensure_network(MGMT_NETWORK, lv.network_xml(
            MGMT_NETWORK, "arbr-mgmt", self.settings.mgmt_subnet,
            dhcp_hosts=[(v.mgmt_mac, v.mgmt_ip) for v in self._all_exam_vms()]), paths.TMP, sd)
        lv.ensure_network(LAB_NETWORK, lv.network_xml(
            LAB_NETWORK, "arbr-lab", self.settings.lab_subnet, ipv6=self.ipv6_prefix), paths.TMP, sd)

    def _all_exam_vms(self) -> list[LabVM]:
        """DHCP reservations cover both exams' VMs so either lab works on the shared network."""
        out = list(self.vms)
        other = "rhce" if self.exam == "rhcsa" else "rhcsa"
        try:
            out += Lab(self.settings, other).vms
        except ValueError:
            pass
        return out

    def write_env(self) -> None:
        console_dir = paths.WORKSPACE / "consoles"
        console_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.env_file, {
            "box": vagrant.BOX_NAME,
            "exam": self.exam,
            "provider": self.provider,
            "prefix": self.prefix,
            "pool": POOL,
            "mgmt_network": MGMT_NETWORK,
            "mgmt_subnet": self.settings.mgmt_subnet,
            "lab_network": LAB_NETWORK,
            "iso_path": str(Path(self.settings.iso_path).expanduser().resolve()),
            "console_dir": str(console_dir),
            "vbox_hostonly": "",
            "vms": [{
                "name": v.name, "cpus": v.spec.cpus, "memory": v.spec.memory_mb,
                "mgmt_ip": v.mgmt_ip, "mgmt_mac": v.mgmt_mac, "lab_ip": v.lab_ip, "lab_mac": v.lab_mac,
                "disks": [{"name": d.name, "size_gb": d.size_gb} for d in v.spec.disks],
                "attach_iso": v.spec.role == "utility",
            } for v in self.vms],
        })

    # --- vagrant -------------------------------------------------------------------------
    def vagrant(self, args: list[str], *, on_line: LineFn | None = None, log_file: Path | None = None,
                cancel: threading.Event | None = None, timeout: float | None = 3600) -> Any:
        return vagrant.run_stream(args, self.settings.storage_dir, self.env_extra(), on_line=on_line,
                                  log_file=log_file, cancel=cancel, timeout=timeout)

    def _vagrant_up(self, names: list[str], step: StepFn, line: LineFn | None, log_file: Path,
                    cancel: threading.Event | None) -> None:
        for name in names:
            ledger.record("libvirt-domain", self.vm(name).domain, self.exam, storage_dir=self.settings.storage_dir)
        for attempt in (1, 2):
            res = self.vagrant(["up", "--no-provision", f"--provider={self.provider}", *names],
                               on_line=line, log_file=log_file, cancel=cancel)
            if res.cancelled:
                raise LabError("cancelled", log_file=log_file)
            if res.ok:
                return
            if "locked" in res.out.lower() and attempt == 1:
                step("Vagrant reported a lock; retrying")
                time.sleep(10)
                continue
            raise LabError(f"vagrant up failed for {', '.join(names)}",
                           "Open the log for details. Common causes: low memory, the box missing, "
                           "or a leftover VM from an interrupted run (Lab → Destroy, then retry).", log_file)

    # --- provisioning ----------------------------------------------------------------------
    def _script(self, name: str) -> str:
        common = (paths.VAGRANT_DIR / "provision" / "common.sh").read_text()
        body = (paths.VAGRANT_DIR / "provision" / name).read_text()
        return common + "\n" + body

    def _env_for(self, v: LabVM, root_password: str = "") -> dict[str, str]:
        facts = labfacts.build(self.exam, self.settings.profile, self.provider, self.settings.lab_subnet,
                               self.settings.mgmt_subnet)
        hosts = ";".join(f"{x.lab_ip} {x.lab_ip6} {x.spec.fqdn} {x.name}" for x in self.vms)
        return {
            "AR_NAME": v.name, "AR_FQDN": v.spec.fqdn, "AR_ROLE": v.spec.role, "AR_EXAM": self.exam,
            "AR_MGMT_MAC": v.mgmt_mac, "AR_LAB_MAC": v.lab_mac, "AR_LAB_IP": v.lab_ip,
            "AR_LAB_PREFIX": str(facts["prefix"]), "AR_GATEWAY": facts["gateway"], "AR_DNS": facts["dns"],
            "AR_DOMAIN": facts["domain"], "AR_IPV6": v.lab_ip6, "AR_LAB_NETWORK": facts["network"],
            "AR_HOSTS": hosts, "AR_ROOT_PASSWORD": root_password,
        }

    def provision(self, name: str, script: str, *, root_password: str = "", line: LineFn | None = None,
                  log_file: Path | None = None, timeout: float = 3600) -> None:
        v = self.vm(name)
        t = self.target(name)
        if not remote.wait_reachable(t, timeout=600):
            raise LabError(f"{name} is not reachable over SSH after boot", log_file=log_file)
        res = remote.stream_script(t, self._script(script), env=self._env_for(v, root_password),
                                   timeout=timeout, log_file=log_file,
                                   on_line=(lambda s: line(f"[{name}] {s}")) if line else None)
        if not res.ok:
            raise LabError(f"provisioning {name} failed", res.tail(8), log_file)

    def reboot(self, names: list[str], *, timeout: float = 600) -> dict[str, str]:
        """Reboot from inside the guests and wait until each is back (new boot_id)."""
        before = {n: remote.boot_id(self.target(n)) for n in names}
        for n in names:
            remote.run_cmd(self.target(n), "systemctl reboot", timeout=15)
            remote.close_master(self.target(n))
        problems: dict[str, str] = {}
        deadline = time.monotonic() + timeout
        pending = set(names)
        while pending and time.monotonic() < deadline:
            for n in list(pending):
                bid = remote.boot_id(self.target(n))
                if bid and bid != before.get(n):
                    pending.discard(n)
            time.sleep(4)
        for n in pending:
            problems[n] = "did not come back after reboot"
        return problems

    def discovered_facts(self) -> dict[str, dict[str, str]]:
        out: dict[str, dict[str, str]] = {}
        for v in self.vms:
            res = remote.run_cmd(self.target(v.name), "cat /etc/autorelabel/facts 2>/dev/null", timeout=20)
            facts = {}
            for line in res.out.splitlines():
                if "=" in line:
                    k, val = line.split("=", 1)
                    facts[k.strip()] = val.strip()
            if "lab_nic" in facts:
                facts["nic"] = facts["lab_nic"]
            out[v.name] = facts
        return out

    def facts(self, discovered: dict[str, Any] | None = None) -> dict[str, Any]:
        if discovered is None:
            discovered = self.state().get("discovered", {})
        return labfacts.build(self.exam, self.settings.profile, self.provider, self.settings.lab_subnet,
                              self.settings.mgmt_subnet, discovered)

    def health_check(self) -> list[str]:
        """Verify the utility services from a node's point of view (what candidates will use)."""
        problems = []
        u = self.target("utility")
        checks = {
            "repository": "curl -fsS -o /dev/null http://127.0.0.1/rhel10/BaseOS/repodata/repomd.xml",
            "flatpak repository": "test -s /var/www/html/flatpak/repo/summary",
            "extras repository": "test -s /var/www/html/extras/repodata/repomd.xml",
            "DNS": f"getent hosts utility.{labfacts.DOMAIN} >/dev/null || "
                   f"python3 -c \"import socket;socket.gethostbyname('utility.{labfacts.DOMAIN}')\"",
            "NTP server": "chronyc -n serverstats >/dev/null",
            "NFS server": "systemctl is-active -q nfs-server",
        }
        for label, cmd in checks.items():
            res = remote.run_cmd(u, cmd, timeout=30)
            if not res.ok:
                problems.append(f"utility: {label} not working ({res.tail(2)})")
        return problems

    # --- bring-up --------------------------------------------------------------------------
    def up(self, *, root_passwords: dict[str, str], on_step: StepFn | None = None,
           on_line: LineFn | None = None, cancel: threading.Event | None = None) -> Path:
        step = on_step or (lambda s: None)
        log_file = log.operation_log(f"lab-up-{self.exam}")
        ok, msg = box.box_status(self.settings, self.provider)
        if not ok:
            raise LabError(f"RHEL 10 box not ready: {msg}", "Build the box first (Lab → Build box).", log_file)
        step("Preparing host networks and storage")
        self.prepare_host()
        self.write_env()
        self.save_state(exam=self.exam, profile=self.settings.profile, provider=self.provider,
                        phase="provisioning", started=time.time())

        step("Starting the utility server")
        self._vagrant_up(["utility"], step, on_line, log_file, cancel)
        step("Configuring the utility server (repositories, DNS, NTP, NFS, Flatpak)")
        self.provision("utility", "utility.sh", line=on_line, log_file=log_file)

        others = [v.name for v in self.vms if v.spec.role != "utility"]
        step(f"Starting {', '.join(others)}")
        self._vagrant_up(others, step, on_line, log_file, cancel)
        step("Configuring the exam nodes")
        errors: list[str] = []

        def prov(n: str) -> None:
            try:
                self.provision(n, "node.sh", root_password=root_passwords.get(n, ""), line=on_line,
                               log_file=log_file)
            except LabError as exc:
                errors.append(f"{n}: {exc} {exc.hint}")

        with ThreadPoolExecutor(max_workers=len(others)) as pool:
            list(pool.map(prov, others))
        if errors:
            raise LabError("node provisioning failed", "; ".join(errors), log_file)

        step("Rebooting every VM to verify the baseline survives a reboot")
        problems = self.reboot(self.names())
        if problems:
            raise LabError("VM(s) did not come back after the verification reboot",
                           "; ".join(f"{k}: {v}" for k, v in problems.items()), log_file)
        step("Checking lab services")
        problems_list = self.health_check()
        if problems_list:
            raise LabError("lab health check failed", "; ".join(problems_list), log_file)
        self.save_state(discovered=self.discovered_facts(), phase="baseline")
        return log_file

    # --- power, snapshots, teardown -------------------------------------------------------
    def power_states(self) -> dict[str, tuple[str, str]]:
        return {v.name: lv.state(v.domain) for v in self.vms}

    def exists(self) -> bool:
        return any(lv.domain_exists(v.domain) for v in self.vms)

    def snapshot_all(self, name: str, description: str = "") -> None:
        """Offline (disk-only) snapshot of every VM: shut down, snapshot, leave off."""
        for v in self.vms:
            remote.close_master(self.target(v.name))
            if lv.state(v.domain)[0] != "shut off" and not lv.shutdown(v.domain, wait=180):
                lv.destroy(v.domain)
        for v in self.vms:
            if name in lv.snapshots(v.domain):
                lv.snapshot_delete(v.domain, name)
            res = lv.snapshot_create(v.domain, name, description)
            if not res.ok:
                raise LabError(f"snapshot of {v.name} failed: {res.tail(3)}")

    def start_all(self, names: list[str] | None = None) -> None:
        for net in (MGMT_NETWORK, LAB_NETWORK):
            if not lv.network_active(net):
                lv.virsh("net-start", net)
        for n in names or self.names():
            v = self.vm(n)
            if lv.state(v.domain)[0] in ("shut off", "crashed"):
                lv.start(v.domain)
            elif lv.state(v.domain)[0] == "paused":
                lv.resume(v.domain)

    def wait_all(self, names: list[str] | None = None, timeout: float = 600) -> list[str]:
        missing = []
        for n in names or self.names():
            if not remote.wait_reachable(self.target(n), timeout=timeout):
                missing.append(n)
        return missing

    def revert(self, snapshot: str, names: list[str] | None = None) -> None:
        for n in names or self.names():
            v = self.vm(n)
            remote.close_master(self.target(n))
            lv.destroy(v.domain)
            res = lv.snapshot_revert(v.domain, snapshot)
            if not res.ok:
                raise LabError(f"could not revert {n} to {snapshot}: {res.tail(3)}")

    def pause_all(self) -> None:
        for v in self.vms:
            if lv.state(v.domain)[0] == "running":
                lv.suspend(v.domain)

    def resume_all(self) -> None:
        for v in self.vms:
            if lv.state(v.domain)[0] == "paused":
                lv.resume(v.domain)
                lv.time_sync(v.domain)

    def destroy(self, *, on_line: LineFn | None = None) -> None:
        log_file = log.operation_log(f"lab-destroy-{self.exam}")
        for v in self.vms:
            remote.close_master(self.target(v.name))
            for s in lv.snapshots(v.domain):
                lv.snapshot_delete(v.domain, s)
        if self.env_file.exists():
            self.vagrant(["destroy", "-f"], on_line=on_line, log_file=log_file, timeout=900)
        for v in self.vms:  # anything Vagrant didn't manage to remove
            if lv.domain_exists(v.domain):
                lv.destroy(v.domain)
                lv.virsh("undefine", v.domain, "--remove-all-storage", "--snapshots-metadata", timeout=120)
        STATE_FILE.unlink(missing_ok=True)
