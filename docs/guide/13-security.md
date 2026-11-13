# Security and your computer

autorelabel builds virtual machines on your computer and runs an exam in them. This page explains what it does to your computer and what it can't do, so you can decide whether to run it. Everything here can be checked in the repository's source.

## Who it runs as

autorelabel runs as your own user, with your user's rights. It never asks for your password, and it never runs `sudo` on its own.

`sudo` runs only when you ask the doctor to install what's missing, with `./autorelabel doctor --fix` or **Fix for me** in the host check. It shows you every command first and waits for your yes. Then it runs exactly those commands in your terminal, in that order, and stops at the first one that fails. `sudo` asks for your password itself, so autorelabel never sees it.

> **Which commands can `doctor --fix` run?**
> Only the ones written for your distribution in [`distro-guides.yaml`](../../src/autorelabel/data/distro-guides.yaml): packages from your distribution, HashiCorp's repository where your distribution doesn't ship Vagrant or Packer, starting libvirt's service, joining the `libvirt`, `kvm` or `vboxusers` group, and `setfacl` lines that let the VM user pass through the folders on the way to your lab storage and your ISO. Steps that need a download page or the AUR are only shown, never run. Every command is recorded with the command that undoes it, and the uninstaller lists those for you.

With libvirt, the VMs run as the system's VM user (`libvirt-qemu` or `qemu`), like any libvirt VM. With VirtualBox, they run as you, in a VirtualBox profile of their own, so they never appear in your VirtualBox window.

## What it changes on your computer

Everything autorelabel creates goes in three places:

- the repository folder: `.venv/` (its Python libraries) and `.workspace/` (settings, sessions, history and logs)
- the lab storage folder you chose at setup: the VM disks, the box build and Packer's plugins
- the hypervisor's own lists: the box, the VMs, two lab networks and a storage pool

[Files and uninstalling](10-files-and-uninstall.md) lists each of them. Each resource is written to a ledger the moment it's created, and `./autorelabel uninstall` removes what the ledger lists, never something that only has a similar name.

It doesn't edit your system configuration, your firewall, your shell or desktop settings, your own VMs or your other Vagrant projects. Vagrant's shared folder is turned off, because with libvirt it would edit your computer's `/etc/exports`.

## The lab's network

As autorelabel sets them up, the lab VMs can't reach the internet or your local network, and no other computer can reach them. They can talk to your computer itself, at its own address on the lab's networks, like any VM on a host-only network. Which of your computer's services answer there is up to its firewall. A service that listens only on your computer's `127.0.0.1` is out of their reach.

| | libvirt | VirtualBox |
|---|---|---|
| Management network (how autorelabel reaches the VMs) | Isolated: libvirt gives it no route out | VirtualBox NAT. The VMs are set up with no route through it, so nothing goes out. That is a setting inside each VM: whoever is root in a VM (you, during an exam) can add a route through it and be online from that VM. The way from a VM to your computer's own `127.0.0.1` is turned off |
| Lab network (the one you configure) | Isolated in the same way | Host-only: only your computer joins it |
| SSH into the VMs | Over the isolated management network | A port forward that listens only on `127.0.0.1` |
| The VM screens | VNC on `127.0.0.1` only | None: the VMs run headless, and the serial console is a socket in a folder only you can open |

The results dashboard (`./autorelabel dashboard`) is a web server on `127.0.0.1` that runs only while you keep the command open. It is read-only, it has no script in its pages, and it loads nothing from elsewhere: its fonts come from autorelabel itself. It answers only to the browser that opened the address it printed, it refuses requests made under any other host name, and it refuses connections from programs of another user of your computer, which it checks with the kernel before it looks at what was asked for.

VS Code in the browser (RHCE) runs inside the control node. autorelabel forwards it through SSH to `127.0.0.1` on your computer (port 18080, or the next free one), and only while the exam runs.

> **Why does the lab have no internet?**
> The real exam has none either. The software repositories come from your own DVD, served inside the lab by the utility server, and the nodes never need a subscription.

## What it downloads

The lab itself is always offline. autorelabel downloads only these, once each, and every version is pinned:

- **The first run:** its Python libraries from PyPI, each verified by checksum.
- **The box build:** Packer's plugins from GitHub. Your ISO is checked against Red Hat's published SHA-256 for the RHEL 10.0 and 10.2 DVDs, so a damaged or altered DVD image is refused. For a version with no published checksum, autorelabel says so and shows the ISO's checksum, for you to compare with Red Hat's download page.
- **Before the first RHCE exam:** the Ansible collections, Python wheels (each verified by checksum, at download and again when the lab installs them) and VS Code in the browser with its extensions (`./autorelabel content download`).

Nothing is uploaded. There is no telemetry and no account, and autorelabel turns off Vagrant's and Packer's own update checks. A problem report is a file on your computer. It reaches the project only if you attach it to an issue yourself, and it hides your home folder, user name and host name, and masks passwords.

## Passwords and keys

The lab's passwords are short made-up words, kept in plain text in `.workspace/` because you need them during the exam. They exist only in the lab, so never use one anywhere else. Vagrant gives each VM a new SSH key of its own, kept in the workspace too.

autorelabel never handles your Red Hat account. You download the ISO yourself, and the lab never registers with Red Hat.

> **Can a lab VM do anything to my computer?**
> The VMs are ordinary virtual machines without shared folders. autorelabel reaches them over SSH and reads what the checks print, and it never runs anything a VM sends back. A way for a VM, a task or a bank file to run commands on your computer would be a security problem.

## Reporting a security problem

Please don't open a public issue. The [security policy](../../SECURITY.md) explains what counts as a security problem and how to report one privately.

The repository's own practices, such as pinned dependencies and limited workflow permissions, are scored every week by [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/syed-913/autorelabel-rhcsa-rhce).
