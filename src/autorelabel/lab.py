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

from . import box, labfacts, labspec, ledger, log, paths, providers, remote, vagrant
from .config import Settings
from .fsutil import atomic_write_json, read_json
from .providers import conflict
from .providers import libvirt as lv
from .providers import virtualbox as vb

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
        self.hv = providers.get(self.provider)

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
        if self.provider == "virtualbox":
            # VirtualBox reaches the guest through a NAT port forward on 127.0.0.1.
            ssh = (self.state().get("ssh") or {}).get(name)
            if not ssh:
                cfg = vagrant.ssh_config(name, self.settings.storage_dir, self.env_extra())
                if cfg.get("Port"):
                    ssh = {"host": cfg.get("HostName", "127.0.0.1"), "port": int(cfg["Port"])}
                    st = self.state()
                    st.setdefault("ssh", {})[name] = ssh
                    atomic_write_json(STATE_FILE, st)
            if ssh:
                return remote.Target(name=f"{self.exam}-{name}", host=ssh["host"], key=key, port=int(ssh["port"]))
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
        sd = self.settings.storage_dir
        if self.provider == "virtualbox":
            vb.ensure_profile(layout["vbox_home"], layout["vbox_vms"])
            for v in self.vms:
                ledger.record("vbox-vm", v.domain, self.exam, storage_dir=sd)
            layout["vbox_disks"].mkdir(parents=True, exist_ok=True)
            return
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
            "console_dir": str(vb.console_dir()),
            "vbox_paravirt": vb.PARAVIRT,
            "vbox_disk_dir": str(box.storage_layout(self.settings)["vbox_disks"]),
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

    def guard_hypervisors(self) -> None:
        """Refuse to start VMs while the other hypervisor runs some (see providers.conflict)."""
        clash = conflict.check(self.provider)
        if clash:
            raise LabError(*clash)
        if self.provider == "virtualbox":
            try:
                vb.wait_for_own_service(paths.vbox_home(self.settings.storage_dir))
            except vb.ProfileBusy as exc:
                raise LabError(str(exc), exc.hint) from exc

    def _vagrant_up(self, names: list[str], step: StepFn, line: LineFn | None, log_file: Path,
                    cancel: threading.Event | None) -> None:
        self.guard_hypervisors()
        kind = "libvirt-domain" if self.provider == "libvirt" else "vbox-vm"
        for name in names:
            ledger.record(kind, self.vm(name).domain, self.exam, storage_dir=self.settings.storage_dir)
        before_hostonly = vb.hostonly_interfaces() if self.provider == "virtualbox" else set()
        for attempt in (1, 2):
            res = self.vagrant(["up", "--no-provision", f"--provider={self.provider}", *names],
                               on_line=line, log_file=log_file, cancel=cancel)
            if res.cancelled:
                raise LabError("cancelled", log_file=log_file)
            if res.ok:
                if self.provider == "virtualbox":
                    self._vbox_after_up(names, before_hostonly, step)
                return
            if "locked" in res.out.lower() and attempt == 1:
                step("Vagrant reported a lock; retrying")
                time.sleep(10)
                continue
            # vagrant-libvirt occasionally gives up right after starting a domain ("not ready for
            # guest communication ... a bug should be reported") and removes it again: retry once.
            if "not ready for guest communication" in res.out and attempt == 1:
                step("Vagrant gave up on a VM that was still booting; retrying")
                time.sleep(10)
                continue
            raise LabError(f"vagrant up failed for {', '.join(names)}",
                           "Open the log for details. Common causes: low memory, the box missing, "
                           "or a leftover VM from an interrupted run (Lab → Destroy, then retry).", log_file)

    def _vbox_after_up(self, names: list[str], before: set[str], step: StepFn) -> None:
        """Ledger host-only interfaces Vagrant created and refresh SSH ports. VMs are created in
        the private profile's machine folder (lab storage); one found elsewhere is moved there.
        The lab network loses the DHCP server VirtualBox gave it (it stops serving once the VMs
        power off for the baseline snapshot)."""
        for ifname in sorted(vb.hostonly_interfaces() - before):
            ledger.record("vbox-hostonly", ifname, "created by Vagrant", storage_dir=self.settings.storage_dir)
        folder = box.storage_layout(self.settings)["vbox_vms"]
        st = self.state()
        st.pop("ssh", None)
        atomic_write_json(STATE_FILE, st)
        for name in names:
            dom = self.vm(name).domain
            cfg_path = vb._info(dom).get("CfgFile", "")
            if cfg_path and not cfg_path.startswith(str(folder)):
                step(f"Moving {name} into the lab storage folder")
                remote.close_master(self.target(name))
                vb.shutdown(dom, wait=120) or vb.destroy(dom)
                res = vb.move(dom, folder)
                if not res.ok:
                    _log.warning("movevm %s failed: %s", dom, res.tail(3))
                vb.start(dom)
        for name in names:
            remote.wait_reachable(self.target(name), timeout=300)
        lab_if = vb._info(self.vm(names[0]).domain).get("hostonlyadapter2", "")
        if lab_if and vb.remove_dhcp_server(lab_if):
            _log.info("removed VirtualBox's DHCP server from the lab network (%s)", lab_if)

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
            "AR_LAB_NETWORK6": f"{facts['ipv6_prefix']}/{facts['ipv6_prefixlen']}",
            "AR_HOSTS": hosts, "AR_ROOT_PASSWORD": root_password,
            "AR_STUDENT_PASSWORD": self.accounts().get("student", ""),
            "AR_ANSIBLE_PASSWORD": self.accounts().get("ansible", ""),
            "AR_CODE_SERVER": "yes" if self.settings.code_server else "no",
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

    def accounts(self) -> dict[str, str]:
        """Lab-wide RHCE accounts (student on control, ansible on managed nodes), created
        once per lab build and shown to the candidate."""
        st = self.state()
        acc = st.get("accounts") or {}
        if self.exam == "rhce" and not acc:
            from . import secrets_util

            acc = {"student": secrets_util.password(), "ansible": secrets_util.password()}
            self.save_state(accounts=acc)
        return acc

    def _rhce_content(self) -> dict[str, Path]:
        from . import content

        root = content.content_dir(self.settings)
        ok, msg = content.status(self.settings)
        if not ok:
            raise LabError(f"RHCE content is missing: {msg}",
                           "Run once (needs internet): ./autorelabel content download")
        return {"wheels": root / "wheels", "collections": root / "collections",
                "code-server": root / "code-server", "roles": paths.VAGRANT_DIR / "content" / "roles"}

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
        if self.exam == "rhce":
            items = self._rhce_content()
            step("Publishing Git, collections and roles on the utility server")
            res = remote.upload(self.target("utility"), {"collections": items["collections"], "roles": items["roles"]})
            if not res.ok:
                raise LabError("could not copy content to the utility server", res.tail(3), log_file)
            self.provision("utility", "utility-rhce.sh", line=on_line, log_file=log_file)

        others = [v.name for v in self.vms if v.spec.role != "utility"]
        step(f"Starting {', '.join(others)}")
        self._vagrant_up(others, step, on_line, log_file, cancel)
        step("Configuring the exam nodes")
        errors: list[str] = []

        def prov(n: str) -> None:
            role = self.vm(n).spec.role
            script = {"exam": "node.sh", "managed": "managed.sh", "control": "control.sh"}[role]
            try:
                if role == "control":
                    items = self._rhce_content()
                    res = remote.upload(self.target(n), {k: items[k] for k in ("wheels", "collections",
                                                                               "code-server")})
                    if not res.ok:
                        raise LabError(f"could not copy content to {n}", res.tail(3), log_file)
                self.provision(n, script, root_password=root_passwords.get(n, ""), line=on_line,
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
        return {v.name: self.hv.state(v.domain) for v in self.vms}

    def exists(self) -> bool:
        return any(self.hv.domain_exists(v.domain) for v in self.vms)

    def snapshot_all(self, name: str, description: str = "") -> None:
        """Offline (disk-only) snapshot of every VM: shut down, snapshot, leave off."""
        for v in self.vms:
            remote.close_master(self.target(v.name))
            if self.hv.state(v.domain)[0] != "shut off" and not self.hv.shutdown(v.domain, wait=180):
                self.hv.destroy(v.domain)
        for v in self.vms:
            if name in self.hv.snapshots(v.domain):
                self.hv.snapshot_delete(v.domain, name)
            res = self.hv.snapshot_create(v.domain, name, description)
            if not res.ok:
                raise LabError(f"snapshot of {v.name} failed: {res.tail(3)}")

    def start_all(self, names: list[str] | None = None) -> None:
        if any(self.hv.state(self.vm(n).domain)[0] in ("shut off", "crashed", "paused") for n in names or self.names()):
            self.guard_hypervisors()
        if self.provider == "libvirt":
            for net in (MGMT_NETWORK, LAB_NETWORK):
                if not lv.network_active(net):
                    lv.virsh("net-start", net)
        for n in names or self.names():
            v = self.vm(n)
            if self.hv.state(v.domain)[0] in ("shut off", "crashed"):
                self.hv.start(v.domain)
            elif self.hv.state(v.domain)[0] == "paused":
                self.hv.resume(v.domain)

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
            self.hv.destroy(v.domain)
            res = self.hv.snapshot_revert(v.domain, snapshot)
            if not res.ok:
                raise LabError(f"could not revert {n} to {snapshot}: {res.tail(3)}")

    def pause_all(self) -> None:
        for v in self.vms:
            if self.hv.state(v.domain)[0] == "running":
                self.hv.suspend(v.domain)

    def resume_all(self) -> None:
        for v in self.vms:
            if self.hv.state(v.domain)[0] == "paused":
                self.hv.resume(v.domain)
                self.hv.time_sync(v.domain)

    def destroy(self, *, on_line: LineFn | None = None) -> None:
        log_file = log.operation_log(f"lab-destroy-{self.exam}")
        for v in self.vms:
            remote.close_master(self.target(v.name))
            for s in self.hv.snapshots(v.domain):
                self.hv.snapshot_delete(v.domain, s)
        if self.env_file.exists():
            self.vagrant(["destroy", "-f"], on_line=on_line, log_file=log_file, timeout=900)
        for v in self.vms:  # anything Vagrant didn't manage to remove
            if self.hv.domain_exists(v.domain):
                self.hv.destroy(v.domain)
                if self.provider == "libvirt":
                    lv.virsh("undefine", v.domain, "--remove-all-storage", "--snapshots-metadata", timeout=120)
                else:
                    vb.vbm("unregistervm", v.domain, "--delete", timeout=300)
        STATE_FILE.unlink(missing_ok=True)
