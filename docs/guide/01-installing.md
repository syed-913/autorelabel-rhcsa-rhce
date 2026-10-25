# Installing

Installing autorelabel happens in three parts. First you install a few tools with your distribution's package manager, which is the only step that needs `sudo`. Then you clone the repository. Finally you run `./autorelabel`, which sets itself up, checks your computer, asks three questions and builds the RHEL 10 image that every lab starts from.

## What you need, and why

| Tool | What autorelabel uses it for |
|---|---|
| **Python 3.10 or newer**, with its `venv` module | autorelabel is written in Python. Its libraries are installed into a private folder (`.venv/` inside the repository), so your system Python is never changed. |
| **OpenSSH client** | Connecting to the lab VMs, both for you (`./autorelabel ssh node1`) and for the grader. |
| **Packer** 1.10 or newer | Building the RHEL 10 box from your ISO, once. |
| **Vagrant** 2.3 or newer | Creating and starting the lab VMs from that box. |
| **libvirt with QEMU/KVM** and the **vagrant-libvirt** plugin | The hypervisor (recommended). The plugin lets Vagrant create libvirt VMs. |
| **VirtualBox** 7.2.2 or newer | The alternative hypervisor, if you prefer it to libvirt. |
| **git** | Cloning the repository and, later, updating it. |

> **Why does it need both Packer and Vagrant?**
> They do two different jobs. Packer installs RHEL 10 from your ISO into a ready-made disk image, called a box, and does it only once. Vagrant then creates the lab VMs from that box whenever a lab is needed, which takes a minute or two each time. Without the box, every exam would start with a full RHEL installation.

> **Which hypervisor should I choose?**
> libvirt with KVM, if you can. It is the hypervisor every task was developed and tested on, it is part of Linux, and it starts VMs quickly. VirtualBox works too and is tested with every task, but it has two constraints: autorelabel keeps its VMs in a separate VirtualBox profile, so VirtualBox Manager must be closed while a lab runs, and VirtualBox VMs must never run at the same time as KVM VMs.

The install commands for each distribution are in the README's [Requirements](../../README.md#requirements) section. After running them, **log out and back in** (or reboot). That is what makes the new `libvirt`, `kvm` or `vboxusers` group membership take effect. You can check it with:

```bash
groups
```

The output should include `libvirt` and `kvm` (or `vboxusers` for VirtualBox).

> **I added myself to the group, but the doctor still says I'm not a member. Why?**
> Group membership is read when you log in, so a terminal opened before the change still has the old list. Log out of your desktop session and back in. Opening a new terminal tab is not enough.

## Getting the RHEL 10 ISO

autorelabel runs real Red Hat Enterprise Linux 10, installed from your own copy of the DVD image.

1. Create a free account at [developers.redhat.com](https://developers.redhat.com/register). The free Red Hat Developer subscription allows this kind of personal use.
2. Download **Red Hat Enterprise Linux 10 Binary DVD** for x86_64. The file is called something like `rhel-10.0-x86_64-dvd.iso` and is about 8 GB.
3. Keep it anywhere. The setup looks for it in the repository folder, in `~/Downloads`, in the folder that contains the repository and in your home folder, and you can type a path if it is elsewhere.

> **Can I use the smaller "Boot ISO"?**
> No. The boot ISO doesn't contain the packages, and the lab works offline, so the full DVD is required. autorelabel checks the image's volume label and size and tells you if it is the wrong one.

> **Does autorelabel register anything with Red Hat or use my subscription?**
> No. The box is installed offline from the DVD and is never registered. Your Red Hat account is only needed to download the ISO.

## The first run

Clone the repository and start autorelabel:

```bash
git clone https://github.com/syed-913/autorelabel-rhcsa-rhce.git
cd autorelabel-rhcsa-rhce
./autorelabel
```

Here is what happens next, in order.

### 1. The private Python environment

`./autorelabel` is a small shell script. It checks that your computer runs Linux on x86_64 (not WSL), finds Python 3.10 or newer and creates `.venv/` in the repository. It then installs autorelabel's Python libraries into it, at exact versions verified by checksum. This takes about 30 seconds and needs the internet once. Later runs skip this step unless an update changed the libraries.

> **It says Python's `venv` module is missing. What do I install?**
> The message names the package for your distribution. On Debian and Ubuntu it is `python3-venv`. If you have several Python versions, you can choose one with `AUTORELABEL_PYTHON=python3.12 ./autorelabel`.

### 2. The host check (the doctor)

autorelabel then checks your computer and shows a table of checks: the CPU, `/dev/kvm`, the tools and their versions, your group memberships, free memory, the lab storage folder, the ISO, the lab networks and a few more. A ✔ means the check passed, `!` is a warning, and ✘ must be fixed before you continue.

Select a row with ✘ or `!` to see the exact commands for your distribution, together with the commands that undo them. Press `c` to copy them, run them yourself in another terminal, then press `r` to check again. The doctor never changes anything on your computer by itself.

Every check is explained in [Troubleshooting](09-troubleshooting.md#the-doctors-checks).

### 3. Setup: three questions

When the checks pass, a setup page asks for:

- **The hypervisor:** libvirt/KVM or VirtualBox. Only the ones that passed the checks can be chosen.
- **The lab storage directory:** where the VM disks and build files go. autorelabel creates a folder named `autorelabel` inside the directory you choose and writes nothing else there. The suggestion is `~/.local/share`, so the data ends up in `~/.local/share/autorelabel`. Choose a disk with about 30 GB free (40 GB if you plan to take RHCE exams). The page shows the free space as you type.
- **The RHEL 10 ISO:** the path to the DVD image. The page confirms when it recognises a RHEL 10 DVD.

It also asks for a **resource profile**:

| Profile | RHCSA lab | RHCE lab |
|---|---|---|
| **lite** (recommended) | about 2.8 GB of RAM for the VMs | about 5.3 GB, with 3 managed nodes |
| **standard** | about 4 GB | about 8.5 GB, with 5 managed nodes |

The doctor also wants about 0.75 GB free on top of that for your own desktop.

> **Can I change these answers later?**
> Yes, in Settings. Changing the profile rebuilds the lab automatically at your next exam. Changing the hypervisor needs a box for that hypervisor, which is built the first time you use it. See [Settings](08-settings.md).

> **Why not the usual `/var/lib/libvirt/images`?**
> That folder belongs to the system and needs `sudo` to manage. Keeping everything in one folder you own means autorelabel never needs root, and removing it later is clean.

### 4. Building the box

The last step builds the RHEL 10 box from your ISO. It takes about 10 to 15 minutes, and the screen shows each stage with a progress bar:

1. **Verifying the ISO checksum.** Reading 8 GB takes a minute or two.
2. **Installing Packer plugins.** A small download, needed once.
3. **Installing RHEL from the ISO.** An unattended installation in a temporary VM: no subscription, no repository files left behind, a serial console for the exams that need one.
4. **Adding the box to Vagrant**, under the name `autorelabel/rhel10`.

When it finishes, the home screen shows **Box ready** and you can start an exam. Continue with [Your first exam](02-first-exam.md).

> **Will I have to build the box again?**
> Normally no. One box is built per hypervisor, so you only build again if you switch hypervisors, if you delete it, or if a release note asks for it. You can rebuild it at any time from **Lab and box** on the home screen, or with `./autorelabel box build`.

> **The doctor says "QEMU (user libvirt-qemu) cannot reach" my folder. What does that mean?**
> With libvirt, the VMs run as a separate system user (`libvirt-qemu` on Debian and Ubuntu, `qemu` on Fedora and RHEL). That user needs permission to pass through each folder on the way to your lab storage and your ISO, and home folders are often private. The doctor prints `setfacl` commands that give that user permission to pass through those folders only, without reading their contents, and prints the matching undo commands.

## The first RHCE exam

The RHCE lab needs a few things that aren't on the RHEL DVD: `ansible-navigator`, the `ansible.posix` and `community.general` collections, and code-server with its extensions (VS Code in your browser). The first time you start an RHCE exam, autorelabel offers to download them once (about 60 to 150 MB, from PyPI, Ansible Galaxy, GitHub and Open VSX) at the exact versions the tasks were tested with. After that, RHCE exams work offline too.

## Updating autorelabel

To update, pull the latest version and start autorelabel as usual:

```bash
git pull
./autorelabel
```

If the update changed the Python libraries, the private environment is refreshed automatically. Your settings, history and box are kept.
