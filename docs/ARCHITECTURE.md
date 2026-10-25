# Architecture

autorelabel is one Python application (`src/autorelabel/`) started by a bash bootstrap (`./autorelabel`). It drives Packer and Vagrant to build and run a RHEL 10 lab, generates exams from a task bank, keeps time, and grades the lab after rebooting it.

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

The TUI and the CLI hold no exam logic; both call the engine, which is what lets a browser front end be added later without touching it.

## The lab

`labspec.py` defines the VMs per exam and profile (lite / standard); `labfacts.py` turns that into the facts tasks are rendered with (addresses, disks, URLs, RHCE inventory groups).

- **Box:** `box.py` builds `autorelabel/rhel10` with Packer from the user's own DVD ISO (BIOS boot, serial console, no subscription, no repository files left behind).
- **Networks:** two isolated networks. *Management* (the grader's path: `mgmt0` in the `trusted` zone, the `vagrant` account) and *lab* (what the candidate configures, no internet). libvirt uses dedicated networks and a dedicated storage pool in the lab storage directory; VirtualBox uses NAT plus a host-only network, in a **private VirtualBox profile** (`VBOX_USER_HOME` inside the lab storage). VirtualBox runs one `VBoxSVC` per user, and `VBOX_USER_HOME` only counts when it starts: while one serves another profile, every `VBoxManage` call goes to that profile. `providers/virtualbox.py` therefore waits for such a service to exit before each call (and refuses if VirtualBox Manager or the user's VMs keep it alive), and `conflict.py` reads the process list instead of asking `VBoxManage`.
- **Serial consoles:** libvirt gives each VM a pty that discards what nobody reads. A VirtualBox serial port in server mode (a Unix socket) holds it back instead, and the guest kernel waits on every character of its console messages, so a VM nobody watches boots at a crawl and never answers SSH. `console_keeper.py` (one per user, started before any VirtualBox VM boots, gone 15 minutes after the last one stops) stays connected to each lab VM's console, drops output nobody reads, and relays `autorelabel console` sessions and the grader's probes to the VM.
- **Guest clock on VirtualBox:** VirtualBox offers Linux guests KVM's paravirtual clock, which now and then makes the guest clock jump by centuries right after the boot loader, and the boot stalls. Lab VMs and the Packer build VM use the `minimal` paravirtualization interface instead; `providers/virtualbox.py` sets it before every start, because reverting a snapshot brings back the settings the snapshot was taken with.
- **Disk names on VirtualBox:** the extra disks are SATA (`sdb`, `sdc`) and the sd driver numbers disks asynchronously, so names could change from one boot to the next (in a test, 3 boots in 40 had them out of order, once with the root disk as `sdc`). Tasks name disks in prompts and checks, so the box boots with RHEL's `sd_mod.probe=sync`: names follow the port order. libvirt disks are virtio (`vdX`) and keep their names anyway.
- **No TRIM on VirtualBox:** VirtualBox 7.2's SATA controller can hang for good on a discard request (a box build froze in `fstrim` and could not even power off). The box's disk has discard turned off on VirtualBox, so neither the build nor RHEL's weekly `fstrim.timer` on a lab VM sends one. libvirt keeps discard, which keeps its sparse disk images small.
- **Provisioning:** the app provisions over SSH (`vagrant/provision/*.sh`, streamed with progress markers), not through Vagrant provisioners, so it can retry and verify. The utility VM serves the DVD repositories, Flatpaks, DNS, NTP, NFS, and for RHCE a Git server and Ansible content.
- **RHCE content:** `content.py` downloads, once and on the host (the only step that needs internet), the Python wheels for `ansible-navigator`, the `ansible.posix` and `community.general` collections, code-server and the VS Code extensions. Every version is pinned (the wheels in `vagrant/content/rhce-wheels.txt`), so an upstream release can't change the lab under the self-tested tasks; changing a pin invalidates the cached content. The execution environment is built inside the lab from the DVD's packages and these wheels, so no registry is ever needed.
- **VS Code (code-server):** it listens on `control`'s loopback only. The app opens an SSH tunnel (`ssh -L`, its own control socket) to `127.0.0.1:18080` on the host, because browsers allow the clipboard and the editor's web views only on `localhost` or HTTPS. The tunnel closes when the exam locks or is abandoned.
- **Management addresses:** both exams share the management network, so each exam's VMs get their own fixed addresses (RHCE's start 40 above RHCSA's) and DHCP reservations; a lab left behind by the other exam can't take a VM's address.
- **Snapshots:** `baseline` (a freshly provisioned lab) and `exam-start` (after the task setups). *Retake* and *Reset node* revert to `exam-start`.
- **One hypervisor at a time:** `providers/conflict.py` refuses to start lab VMs while the other hypervisor runs VMs (VirtualBox next to KVM guests can corrupt KVM's CPU state).

## An exam, end to end

1. **Create:** `bank/select.py` draws a blueprint-valid exam from a seed: anchors first, required objective groups, domain quotas, the difficulty mix, exclusive groups and disk budgets; parameters are drawn (pools without replacement). Each node gets a fresh root password.
2. **Prepare:** revert to `baseline`, set the root passwords, import the Red Hat signing keys with `rpm --import` (dnf's own key parsing is unreliable on RHEL 10.0), run the task setups (anchors last) from a temporary setup repository, remove it, snapshot `exam-start`.
3. **Run:** the proctor, a transient `systemd-run --user` unit, keeps time from heartbeats, sends warnings, watches whether the grader can still reach each node, and at zero pauses the VMs.
4. **Grade** (`grader.py`): a pre-reboot pass, a **verified reboot** of every exam node (normal reboot, then ACPI, then reset; a node it cannot reach gets Ctrl+Alt+Del, which systemd turns into a clean reboot even in emergency mode, before a reset; boot problems are diagnosed from the serial console), then the post-reboot pass, which is the only one that counts. Checks are bash scripts run as root over the management network with `set -e` and `pipefail`. An RHCE check can run on an inventory group (`on: "@webservers"`): it becomes one check per host, sharing its weight, and a host where it doesn't apply exits 77 (*n/a*) and is left out of the score instead of counting as passed. Guard checks (nothing else broken) only score once a real check of the task passes.
5. **Report:** points per task (partial or strict), per domain and difficulty, checks that worked only before the reboot, incidents, and the solution guides.

## Sessions and failure handling

`session.py` keeps each session in `.workspace/sessions/<id>/`: `session.json` (written atomically) plus an append-only `events.jsonl` it can be rebuilt from.

```text
new → provisioning → ready → in_progress → locked → grading → graded
          │   ▲                 │   ▲                   │   ▲
          ▼   │                 ▼   │                   ▼   │
   provision_failed         interrupted          grading_interrupted        (any → abandoned)
```

- **Time** accrues in heartbeat steps of at most 20 seconds, so a host crash, suspend or power cut is not counted (configurable). A different `boot_id` on start means the host rebooted: the session becomes *interrupted* and resumes without re-provisioning.
- **Grading** checkpoints after every check and resumes where it stopped.
- **A node that doesn't come back** after the grading reboot is diagnosed (emergency mode, GRUB prompt, kernel panic, SELinux relabel in progress, login prompt but no SSH) and reported; its checks score 0, like on the real exam.
- **Problem reports:** a failure that isn't the user's situation (errors marked `user_fixable` are) makes `report.py` write `.workspace/reports/<time>-<error>.md`: the error and hint, versions, the doctor's checks, the traceback and the end of the operation's log, with the home directory, user and host names replaced and secrets masked. The CLI and TUI then point to the repository's issue form. Nothing is sent anywhere by the app.
- **Host safety:** autorelabel never runs `sudo`, never edits host files outside its directories, and records everything it creates in a ledger (`ledger.py`), which `scripts/uninstall.sh` (pure bash) uses to remove it all again.

## Task bank

`banks/<exam>/` holds `objectives.yaml` (Red Hat's objectives, verbatim, split into facets), `blueprint.yaml` (task count, points, difficulty mix, domain quotas, anchors), `pools.yaml` and `tasks/`. `bank/lint.py` enforces scope (every task maps to official objectives), traceability (every requirement has a check), valid placeholders and test suites; `bank/coverage.py` reports and gates objective coverage. `selftest.py` runs every task on real VMs: pre-state, reference solution, valid alternatives and classic mistakes, each graded after a reboot. It records a digest of each task with its result, per provider (`banks/<exam>/selftest[-virtualbox].json`), so `--changed` re-tests only what changed; `--sweep` runs the suites again once per value of each task's choice parameters, so every value is verified at least once. See [TASK-AUTHORING.md](TASK-AUTHORING.md).

## Files

| Where | What |
|---|---|
| `.workspace/` | settings, sessions, logs, Vagrant state, history (inside the repository, ignored by git) |
| `<lab storage>/autorelabel/` | libvirt pool, VirtualBox profile and VMs, Packer cache and boxes, RHCE content, uninstall ledger and a rescue copy of the uninstaller |
| `$XDG_RUNTIME_DIR/autorelabel/` | SSH control sockets, VirtualBox serial console sockets, the console keeper's socket and lock |

Outside these, the tools autorelabel drives keep their usual state: the Vagrant box in `~/.vagrant.d/boxes/` and entries in Vagrant's machine index, and libvirt's own definitions of the lab's networks, pool and VMs. `./autorelabel uninstall` removes all of it, guided by the ledger (`ledger.tsv`, written before anything is created) and the `autorelabel-` name prefix. Two things stay, because only root can remove them, and autorelabel never runs `sudo`:

- libvirt's QEMU log of each lab VM in `/var/log/libvirt/qemu/` (the uninstaller prints the `sudo rm` command);
- kernel modules the kernel loads on demand for libvirt VMs (`vhost_net`, `tap`, ...), as for any VM; they are gone after the next reboot.

**Footprint audit.** `scripts/dev/footprint.sh <file>` snapshots everything on the host that autorelabel or these tools could change (home directory dotfiles, Vagrant, VirtualBox's default profile, libvirt objects, network interfaces, user units, processes, temporary directories). Take one on a clean host, install and use autorelabel (box build, exam, grading), run `./autorelabel uninstall`, take another and `diff` them: apart from the two items above, they must be identical.

**README media.** `scripts/dev/demo/banner_image.py` draws the README banner (`docs/media/banner.png`, 2x) and the social preview from the TUI banner's real glyphs. `scripts/dev/demo/render.sh` renders the demo video from `demo.py` with [Manim](https://www.manim.community/) (the banner's real glyphs and colours, real bank content) as a 1080p MP4, which is uploaded to the README and release pages on GitHub rather than committed. `scripts/dev/demo/screenshots.py` takes the TUI screenshots: it runs the real app headless in a throwaway workspace, with only the VM power states and the box status stubbed, and gets the results screen from the grader's own scoring.

## Repository layout

```
autorelabel                  # the one command (bash bootstrap)
src/autorelabel/             # engine, grader, proctor, TUI, doctor, providers
banks/rhcsa/  banks/rhce/    # objectives (verbatim), blueprint, tasks
vagrant/  packer/            # lab definition and box build
scripts/uninstall.sh         # pure-bash uninstaller
scripts/dev/                 # footprint audit, RHCE playbook check, README banner, animation and screenshots
docs/                        # coverage reports, architecture, task authoring
docs/guide/                  # the user guide
```
