# Architecture

autorelabel is one Python application (`src/autorelabel/`) started by a bash bootstrap
(`./autorelabel`). It drives Packer and Vagrant to build and run a RHEL 10 lab, generates exams
from a task bank, keeps time, and grades the lab after rebooting it.

```text
./autorelabel ─► bootstrap (bash): checks the host, creates .venv from requirements.lock
                 │
                 ▼
            cli.py ── no arguments ──► tui/ (Textual)          ┐
              │                                                 ├─► engine.py (UI-agnostic service)
              └── subcommands ──► commands.py                   ┘        │
                                                                         ├─ session.py   state machine, journal, time
                                                                         ├─ bank/        objectives, tasks, selection, lint
                                                                         ├─ lab.py       bring-up, snapshots, power
                                                                         │    ├─ vagrant.py, box.py (Packer)
                                                                         │    └─ providers/ libvirt · virtualbox · conflict
                                                                         ├─ grader.py    checks, verified reboot, score
                                                                         ├─ proctor.py   background timer, warnings, lock
                                                                         └─ selftest.py  task quality gate on real VMs
```

The TUI and the CLI hold no exam logic; both call the engine, which is what lets a browser front
end be added later without touching it.

## The lab

`labspec.py` defines the VMs per exam and profile (lite / standard); `labfacts.py` turns that into
the facts tasks are rendered with (addresses, disks, URLs, RHCE inventory groups).

- **Box:** `box.py` builds `autorelabel/rhel10` with Packer from the user's own DVD ISO (BIOS boot,
  serial console, no subscription, no repository files left behind).
- **Networks:** two isolated networks. *Management* (the grader's path: `mgmt0` in the
  `trusted` zone, the `vagrant` account) and *lab* (what the candidate configures, no internet).
  libvirt uses dedicated networks and a dedicated storage pool in the lab storage directory;
  VirtualBox uses NAT plus a host-only network, in a **private VirtualBox profile**
  (`VBOX_USER_HOME` inside the lab storage).
- **Provisioning:** the app provisions over SSH (`vagrant/provision/*.sh`, streamed with progress
  markers), not through Vagrant provisioners, so it can retry and verify. The utility VM serves
  the DVD repositories, Flatpaks, DNS, NTP, NFS, and for RHCE a Git server and Ansible content.
- **Snapshots:** `baseline` (a freshly provisioned lab) and `exam-start` (after the task setups).
  *Retake* and *Reset node* revert to `exam-start`.
- **One hypervisor at a time:** `providers/conflict.py` refuses to start lab VMs while the other
  hypervisor runs VMs (VirtualBox next to KVM guests can corrupt KVM's CPU state).

## An exam, end to end

1. **Create:** `bank/select.py` draws a blueprint-valid exam from a seed: anchors first, required
   objective groups, domain quotas, the difficulty mix, exclusive groups and disk budgets;
   parameters are drawn (pools without replacement). Each node gets a fresh root password.
2. **Prepare:** revert to `baseline`, run the task setups (anchors last), remove the temporary
   setup repository, snapshot `exam-start`.
3. **Run:** the proctor, a transient `systemd-run --user` unit, keeps time from heartbeats, sends
   warnings, watches whether the grader can still reach each node, and at zero pauses the VMs.
4. **Grade** (`grader.py`): a pre-reboot pass, a **verified reboot** of every exam node (normal
   reboot, then ACPI, then reset; boot problems are diagnosed from the serial console), then the
   post-reboot pass, which is the only one that counts. Checks are bash scripts run as root over
   the management network with `set -e` and `pipefail`.
5. **Report:** points per task (partial or strict), per domain and difficulty, checks that worked
   only before the reboot, incidents, and the solution guides.

## Sessions and failure handling

`session.py` keeps each session in `.workspace/sessions/<id>/`: `session.json` (written
atomically) plus an append-only `events.jsonl` it can be rebuilt from.

```text
new → provisioning → ready → in_progress → locked → grading → graded
          │   ▲                 │   ▲                   │   ▲
          ▼   │                 ▼   │                   ▼   │
   provision_failed         interrupted          grading_interrupted        (any → abandoned)
```

- **Time** accrues in heartbeat steps of at most 20 seconds, so a host crash, suspend or power cut
  is not counted (configurable). A different `boot_id` on start means the host rebooted: the
  session becomes *interrupted* and resumes without re-provisioning.
- **Grading** checkpoints after every check and resumes where it stopped.
- **A node that doesn't come back** after the grading reboot is diagnosed (emergency mode, GRUB
  prompt, kernel panic, SELinux relabel in progress, login prompt but no SSH) and reported; its
  checks score 0, like on the real exam.
- **Host safety:** autorelabel never runs `sudo`, never edits host files outside its directories,
  and records everything it creates in a ledger (`ledger.py`), which `scripts/uninstall.sh` (pure
  bash) uses to remove it all again.

## Task bank

`banks/<exam>/` holds `objectives.yaml` (Red Hat's objectives, verbatim, split into facets),
`blueprint.yaml` (task count, points, difficulty mix, domain quotas, anchors), `pools.yaml` and
`tasks/`. `bank/lint.py` enforces scope (every task maps to official objectives), traceability
(every requirement has a check), valid placeholders and test suites; `bank/coverage.py` reports and
gates objective coverage. `selftest.py` runs every task on real VMs: pre-state, reference
solution, valid alternatives and classic mistakes, each graded after a reboot. See
[TASK-AUTHORING.md](TASK-AUTHORING.md).

## Files

| Where | What |
|---|---|
| `.workspace/` | settings, sessions, logs, Vagrant state, history (inside the repository, ignored by git) |
| `<lab storage>/autorelabel/` | libvirt pool, VirtualBox profile and VMs, Packer cache and boxes, RHCE content, uninstall ledger and a rescue copy of the uninstaller |
| `$XDG_RUNTIME_DIR/autorelabel/` | SSH control sockets, VirtualBox serial console sockets |
