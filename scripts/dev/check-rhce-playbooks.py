#!/usr/bin/env python3
"""Syntax-check every playbook the RHCE bank's scripts write, without VMs.

Each reference solution, alternative and mistake test runs in a sandbox where only
`student_write` really writes (into a temporary project); every playbook it produces then goes
through `ansible-playbook --syntax-check`. Use the lab's ansible-core (2.16) and collections:

    pip install "ansible-core==2.16.14"
    ansible-galaxy collection install -p /tmp/collections ansible.posix:==2.2.2 community.general:==11.4.9
    PYTHONPATH=src python scripts/dev/check-rhce-playbooks.py --collections /tmp/collections
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from autorelabel import labfacts  # noqa: E402
from autorelabel.bank import load_bank, render  # noqa: E402
from autorelabel.bank.lint import _sample_params  # noqa: E402

COLLECTIONS = Path()
LAB_ROLES = ROOT / "vagrant/content/roles"

CHECKED: list[str] = []
STUBS = r'''
student_write() { local p="$PROJ/$1"; mkdir -p "$(dirname "$p")"; cat > "$p"; }
as_student() { :; }
student_sh() { :; }
as_user() { :; }
runuser() { :; }
chown() { :; }
ar_ssh_copy_id() { :; }
ar_install() { :; }
ar_new_partition() { echo /dev/null1; }
'''


def inventory(facts: dict) -> str:
    out = []
    for g in ("dev", "test", "prod", "balancers"):
        out.append(f"[{g}]")
        out += [f"{h}.lab.example.com" for h in facts["groups"][g].split()]
    out += ["[webservers:children]", "prod", ""]
    return "\n".join(out)


def check(task, script: Path, facts: dict) -> list[str]:
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        proj = Path(tmp) / "ansible"
        proj.mkdir()
        roles = proj / "roles"
        roles.mkdir()
        for r in LAB_ROLES.iterdir():                      # installed-from-requirements stand-ins
            shutil.copytree(r, roles / r.name)
        shutil.copytree(LAB_ROLES / "lab_webserver", roles / "webserver")
        shutil.copytree(LAB_ROLES / "lab_balancer", roles / "balancer")
        shutil.copytree(LAB_ROLES / "lab_motd", roles / "motd")
        for name in ("rhel-system-roles.timesync", "rhel-system-roles.selinux"):
            (roles / name / "tasks").mkdir(parents=True)
            (roles / name / "tasks/main.yml").write_text("---\n[]\n")
        (proj / "inventory").write_text(inventory(facts))
        (proj / "ansible.cfg").write_text(
            f"[defaults]\ninventory = {proj}/inventory\nroles_path = {roles}\n"
            f"collections_path = {COLLECTIONS}\n")
        env = {**os.environ, **render.env_for(_sample_params(task), facts), "PROJ": str(proj),
               "AR_STUDENT_PASSWORD": "pw", "AR_ANSIBLE_PASSWORD": "pw", "AR_NODE": "control"}
        scripts = [s for s in task.setup_scripts.values()] + [script]
        for s in scripts:
            body = s.read_text().replace("/home/student/ansible", str(proj))
            subprocess.run(["bash", "-c", STUBS + body], env=env, cwd=proj, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        for pb in sorted(proj.rglob("*.yml")):
            if "roles" in pb.relative_to(proj).parts or pb.name.startswith(("requirements",)):
                continue
            text = pb.read_text()
            try:
                doc = yaml.safe_load(text)
            except yaml.YAMLError as exc:
                problems.append(f"{script.parent.name}/{script.name} -> {pb.name}: YAML: {exc}")
                continue
            if not (isinstance(doc, list) and doc and isinstance(doc[0], dict) and "hosts" in doc[0]):
                continue                                  # inventories, vars files, task files
            CHECKED.append(f"{task.id}:{script.name}:{pb.name}")
            log = Path(tmp) / "out.log"
            with open(log, "w") as fh:
                r = subprocess.run(["ansible-playbook", "--syntax-check", str(pb)],
                                   cwd=proj, stdin=subprocess.DEVNULL, stdout=fh, stderr=fh,
                                   env={**os.environ, "ANSIBLE_CONFIG": str(proj / "ansible.cfg"),
                                        "ANSIBLE_NOCOLOR": "1"}, timeout=120)
            if r.returncode != 0:
                msg = log.read_text().strip().splitlines()
                problems.append(f"{script.parent.name}/{script.name} -> {pb.name}: " +
                                " | ".join(m for m in msg if m.strip())[-600:])
    return problems


def main() -> int:
    global COLLECTIONS
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--collections", required=True, type=Path,
                    help="directory with ansible_collections/ (ansible.posix, community.general)")
    COLLECTIONS = ap.parse_args().collections.resolve()
    if not shutil.which("ansible-playbook"):
        print("ansible-playbook not found in PATH (pip install ansible-core==2.16.14)", file=sys.stderr)
        return 2
    bank = load_bank("rhce")
    facts = labfacts.sample("rhce", "lite")
    bad = 0
    for tid, task in sorted(bank.tasks.items()):
        scripts = list(task.solution_scripts.values()) + task.tests("alt") + task.tests("mistake")
        for s in scripts:
            for p in check(task, s, facts):
                bad += 1
                print(f"{tid}: {p}\n")
    print(f"{len(CHECKED)} playbook runs syntax-checked across {len({c.split(':')[0] for c in CHECKED})} tasks")
    missing = sorted(set(bank.tasks) - {c.split(':')[0] for c in CHECKED})
    print("tasks with no playbook checked:", missing)
    print(f"{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
