<div align="center">

```
 █████╗ ██╗   ██╗████████╗ ██████╗ ██████╗ ███████╗██╗      █████╗ ██████╗ ███████╗██╗
██╔══██╗██║   ██║╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝██║     ██╔══██╗██╔══██╗██╔════╝██║
███████║██║   ██║   ██║   ██║   ██║██████╔╝█████╗  ██║     ███████║██████╔╝█████╗  ██║
██╔══██║██║   ██║   ██║   ██║   ██║██╔══██╗██╔══╝  ██║     ██╔══██║██╔══██╗██╔══╝  ██║
██║  ██║╚██████╔╝   ██║   ╚██████╔╝██║  ██║███████╗███████╗██║  ██║██████╔╝███████╗███████╗
╚═╝  ╚═╝ ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝
```

# autorelabel: RHCSA & RHCE practice exam simulator for RHEL 10

**Timed, auto-graded, hands-on RHCSA (EX200) and RHCE (EX294) practice exams on real RHEL 10 virtual
machines, graded *after a reboot*, just like the real thing.**

`touch /.autorelabel`: forget it after `rd.break` and your node won't let you log in. You'll never forget again.

</div>

---

## What it is

`autorelabel` builds a small RHEL 10 lab on your Linux machine (with libvirt/KVM or VirtualBox),
gives you a **20-task RHCSA exam** with a **180-minute timer**, then **reboots every node and grades
your work out of 300** (pass mark 210), the way Red Hat's performance-based exams do.

- **Real RHEL 10**: a Vagrant box built *once* from **your own** RHEL 10 DVD ISO (free Red Hat
  Developer account). No subscription is used anywhere; the lab is fully offline like the exam.
- **Exam-like start**: one node has no network yet (configure it from the console), the other
  node's root password is unknown (interrupt the boot and reset it), and repositories must be
  configured. That's how most real RHCSA exams begin.
- **Graded after a reboot**: every node is rebooted before grading, so only persistent configuration
  counts. Work that *"passed before the reboot but not after"* is flagged so you learn exactly what
  wasn't persistent.
- **Honest, method-agnostic grading**: checks look at the final state (UUID *or* LABEL, `nmcli`
  *or* keyfiles, `parted` *or* `fdisk`…), never at the commands you typed.
- **Every task self-tested on real VMs**: setup, reference solution, accepted alternatives and
  the classic mistakes (`chcon` instead of `semanage fcontext`, firewall rules without `--permanent`,
  `setenforce` without the config file…) are all verified on a real RHEL 10 VM before a task ships.
- **Full objective coverage**: the bank maps every task to Red Hat's **current, verbatim
  objectives**; see [docs/COVERAGE-RHCSA.md](docs/COVERAGE-RHCSA.md).
- **Difficulty levels**: every task is *easy* (10 pts), *medium* (15) or *hard* (20) by a written
  rubric; each exam has the same mix, so scores are comparable.
- **One command, a friendly TUI**: setup wizard, live countdown, node power controls, serial
  console, results with explanations and official-docs references.
- **Leaves your host clean**: one command removes everything it created.

> Not affiliated with or endorsed by Red Hat. Built only from Red Hat's public exam objectives and
> documentation. Contains **no** real exam content. RHCSA, RHCE and RHEL are trademarks of
> Red Hat, Inc.

## Supported hosts

| Host | Status |
|---|---|
| **Linux x86_64** (Ubuntu/Debian, Fedora, RHEL/Alma/Rocky/CentOS Stream, Arch, openSUSE) | ✅ libvirt/KVM (recommended) or VirtualBox 7.2+ |
| Windows 10/11 | ❌ **Not supported yet**: planned for v2 (VirtualBox) |
| WSL2 | ❌ Not supported |
| macOS | ❌ Not supported |

Requirements: an x86-64-v3 CPU (Intel Haswell / AMD Excavator or newer; RHEL 10 requires it),
virtualization enabled in the BIOS, **about 3 GB free RAM** (RHCSA, *lite* profile; about 5.5 GB
for RHCE) and **about 30 GB free disk** in a directory of your choice (40 GB for RHCE).

> **libvirt and VirtualBox on the same machine:** you can have both installed, but never run
> VirtualBox VMs while KVM/libvirt VMs are running (or the other way round). On some kernel and
> VirtualBox versions this freezes every KVM guest (`kvm_intel: vmwrite failed` in the kernel log).
> autorelabel checks before it starts any lab VM and tells you which VMs to shut down first.

With VirtualBox, the lab VMs live in autorelabel's **own VirtualBox profile** inside your lab
storage directory, so they don't appear in (or depend on) your normal VirtualBox VM list. To look at
them in the VirtualBox GUI: `VBOX_USER_HOME=<lab storage>/autorelabel/virtualbox/profile virtualbox`.

## Quick start

```bash
git clone https://github.com/<you>/autorelabel-rhcsa-rhce.git
cd autorelabel-rhcsa-rhce
./autorelabel
```

That's it. The first run:

1. sets up a private Python environment (`.venv/`, nothing installed system-wide),
2. checks your host and shows the exact install commands **for your distribution** for anything
   missing (Vagrant, Packer, libvirt/vagrant-libvirt or VirtualBox),
3. asks three questions (hypervisor, where to store VM disks, where your RHEL 10 ISO is),
4. builds the RHEL 10 box once (about 10–15 minutes),

and then you can start an exam. Afterwards `./autorelabel rhcsa` jumps straight into a new exam.

### Getting the RHEL 10 ISO

Create a free [Red Hat Developer](https://developers.redhat.com/register) account and download the
**Red Hat Enterprise Linux 10 Binary DVD** (x86_64, about 8 GB). Put it anywhere; the setup wizard
finds it in the repository folder or `~/Downloads`.

## Taking an exam

- **New exam**: 20 tasks are drawn from the bank with a fixed blueprint (6 easy · 8 medium · 6 hard,
  every objective domain represented), with randomized names, sizes and ports. The lab is prepared
  (about 2–5 minutes) and the clock starts when you press **Start**.
- **Working**: use your own terminals: `./autorelabel ssh node1` (root over SSH) and
  `./autorelabel console node2` (serial console for GRUB, `rd.break`, emergency mode; `Ctrl+]` to
  leave). Or press `n` on a node in the exam screen.
- **Time**: warnings at 30/10/5/1 minutes appear in the TUI and **inside your SSH sessions**. At zero
  the lab is **frozen** and graded automatically, even if you closed the TUI.
- **Results**: score out of 300, PASS/FAIL, points per difficulty and objective domain, every check
  with ✔/✘, persistence warnings, and a solution with official-documentation references for each task.
- **Retake** the same exam from its starting point, or start a new one.
- **Practice mode**: pick any tasks, untimed, check your work at any time (with or without a
  reboot), read the solution.

### If something goes wrong

| Situation | What happens |
|---|---|
| Your computer crashes, reboots or sleeps during an exam | Downtime is not counted. Reopen `./autorelabel` and resume. |
| A node doesn't come back after the grading reboot | The grader reads its serial console and tells you why (emergency mode/fstab, GRUB prompt, kernel panic, locked out). That node scores 0, like in the real exam. |
| A node hangs or you powered it off | Power on / reset it from the exam screen. |
| You broke a node completely | "Reset to exam start" restores just that node (losing its work). |
| You changed `mgmt0` or the `vagrant` account | You get a warning within two minutes. They are how your work is graded. |

## Removing everything

```bash
./autorelabel uninstall --dry-run   # show what would be removed
./autorelabel uninstall             # remove it
```

This deletes the lab VMs and snapshots, the libvirt pool and networks, the Vagrant box, the VM
storage folder, and `.workspace/` and `.venv/` in the repository. Your ISO is kept. Everything is
tracked in a ledger as it is created, and a rescue copy of the uninstaller lives in the VM storage
folder in case you delete the repository first. It never runs `sudo`; it prints undo commands for
anything you installed yourself.

## What the RHCSA lab looks like

| VM | Role | RAM (lite / standard) |
|---|---|---|
| `utility` | Red Hat's "classroom server": BaseOS/AppStream repositories from your DVD, the official **Red Hat Flatpaks** (Firefox, Thunderbird, `com.redhat.Platform`), DNS for `lab.example.com`, NTP, NFS exports | 768 MB / 1 GB |
| `node1` | Exam node (two extra disks) | 1 GB / 1.5 GB |
| `node2` | Exam node (one extra disk) | 1 GB / 1.5 GB |

Networks are isolated (no internet, no access to your LAN). Nothing in the lab uses a Red Hat
subscription.

## What the RHCE lab looks like

| VM | Role | RAM (lite / standard) |
|---|---|---|
| `utility` | Everything above, plus a Git server (HTTP) and the Ansible collections and roles the tasks install | 1 GB / 1 GB |
| `control` | Where you work, as `student`: `ansible-core` and the RHEL system roles from your DVD, `ansible-navigator`, an execution environment built offline from your DVD, and **VS Code in your browser** (code-server with the Red Hat Ansible extension) | 2 GB / 2.5 GB |
| `node1`… | Managed nodes with an `ansible` user (3 in *lite*, 5 in *standard*), each with a spare disk | 768 MB / 1 GB |

The inventory groups (`dev`, `test`, `prod`, `balancers`, and `webservers` with `prod` as a child)
are shown in the exam instructions. The first RHCE session downloads its Ansible content once
(PyPI, Ansible Galaxy, and for code-server GitHub and Open VSX); after that everything is offline.

## FAQ

**Is there a free RHCSA practice exam for RHEL 10?**
Yes, this project. Exams are generated from a bank covering every current EX200 objective, run on
real RHEL 10 VMs, and are graded automatically after a reboot.

**How do I practice the RHCSA on RHEL 10 at home?**
Install libvirt (or VirtualBox), download the RHEL 10 DVD with a free developer account, clone this
repository and run `./autorelabel`.

**Does it cover the new RHEL 10 objectives (Flatpak, systemd timers…)?**
Yes. The bank follows the current EX200 objectives verbatim, including Flatpak repositories and
applications.

**Do I need a Red Hat subscription?**
No. Only a free Red Hat Developer account to download the ISO. The box is installed offline and
never registered.

**Can I use AlmaLinux or Rocky Linux instead of RHEL?**
Not in v1: the exam is on RHEL 10, and so is the simulator.

**Does it work on Windows?**
Not yet. Windows (VirtualBox) support is planned for v2.

**How close is the grading to Red Hat's?**
Red Hat's grader is secret. autorelabel checks the final state after a reboot, accepts any valid
method, and awards partial credit per check (switch to all-or-nothing in Settings).

**Where do the tasks come from?**
Only from Red Hat's published objectives and RHEL 10 documentation, never from real exam content.

## Project layout

```
autorelabel                  # the one command (bash bootstrap)
src/autorelabel/             # engine, grader, proctor, TUI, doctor, providers
banks/rhcsa/                 # objectives (verbatim), blueprint, tasks
vagrant/  packer/            # lab definition and box build
scripts/uninstall.sh         # pure-bash uninstaller
docs/                        # coverage reports and architecture
```

## License

[MIT](LICENSE)
