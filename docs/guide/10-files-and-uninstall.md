# Files and uninstalling

autorelabel keeps everything it creates in a few known places, records each one in a ledger as it goes, and removes all of it with one command. This page lists those places and explains the uninstaller.

## What autorelabel creates, and where

### In the repository folder

| Path | Contents |
|---|---|
| `.venv/` | The private Python environment with autorelabel's libraries. |
| `.workspace/config.json` | Your settings. |
| `.workspace/sessions/` | One folder per exam or practice session: its tasks, events, results (`results.json`, `report.md`) and grading progress. |
| `.workspace/history.jsonl` | One line per graded attempt, used by **Progress and history**. |
| `.workspace/logs/` | Logs (see [Troubleshooting](09-troubleshooting.md#logs)). |
| `.workspace/reports/` | Problem reports. |
| `.workspace/ledger.tsv` | The ledger: every resource autorelabel has created on this computer. |
| `.workspace/doctor-pending.json` | Undo commands for fixes the doctor has shown you but hasn't yet seen in place. |
| `.workspace/vagrant/`, `.workspace/tmp/`, `.workspace/known_hosts` | Vagrant's state for the lab, temporary files, and the lab VMs' SSH host keys. |

### In the lab storage directory

Everything here is inside one subfolder, `<lab storage>/autorelabel/` (for example `~/.local/share/autorelabel/`):

| Path | Contents |
|---|---|
| `libvirt-pool/` | The libvirt storage pool: the lab VMs' disks and snapshots. |
| `virtualbox/` | With VirtualBox: autorelabel's own VirtualBox profile, its VMs and their disks. |
| `packer/` | Packer's plugins and cache, and the temporary build of the box. |
| `boxes/` | The built box files and their manifest (which ISO, when, which hypervisor). |
| `content/` | The RHCE content: Python wheels, collections, code-server. |
| `ledger.tsv`, `uninstall.sh` | A copy of the ledger and of the uninstaller (see below). |

### Elsewhere on your computer

| What | Where |
|---|---|
| The box `autorelabel/rhel10` | Vagrant's box store, `~/.vagrant.d/boxes/`. |
| Lab VMs | libvirt: domains named `autorelabel-<exam>-<vm>`, such as `autorelabel-rhcsa-node1`. VirtualBox: in autorelabel's own profile, never in your VM list. |
| Lab networks | libvirt: `autorelabel-mgmt` and `autorelabel-lab` (bridges `arbr-mgmt` and `arbr-lab`). VirtualBox: a host-only interface such as `vboxnet0`. |
| Storage pool | libvirt: a pool named `autorelabel`, pointing at `libvirt-pool/` above. |
| The proctor | A temporary systemd user service, `autorelabel-proctor-<session>`, which ends with the exam. |

> **What does autorelabel never touch?**
> Your system configuration, `/var/lib/libvirt/images`, your own VirtualBox VMs and settings, your other Vagrant projects, and anything that needs `sudo`. When something needs `sudo`, such as installing a package or joining a group, autorelabel shows you the command and you run it.

> **What is the ledger?**
> A plain text file that records each resource (a VM, a network, the box, a folder) at the moment autorelabel creates it. The uninstaller reads it to know what to remove, so it never has to guess, and so it never removes something that only happens to have a similar name.

## Uninstalling

Look first, then remove:

```bash
./autorelabel uninstall --dry-run   # list everything that would be removed
./autorelabel uninstall             # remove it (asks for confirmation)
```

This removes the lab VMs and their snapshots, the libvirt pool and networks (or autorelabel's VirtualBox VMs, profile and host-only network), the Vagrant box and autorelabel's entries in Vagrant's machine index, the lab storage subfolder, and `.workspace/` and `.venv/` in the repository.

| Option | What it does |
|---|---|
| `--dry-run` | Only lists what would be removed. |
| `--yes` | Doesn't ask for confirmation. |
| `--keep-box` | Keeps the RHEL 10 box, so a reinstall doesn't have to build it again. |
| `--delete-iso` | Also deletes your RHEL 10 ISO. Without it, the ISO is kept. |

> **Does it remove Vagrant, Packer, libvirt or VirtualBox?**
> No. You installed those yourself with `sudo`, and you might use them for other things. When you fix something the doctor shows you (a package, a group membership, a `setfacl` permission), autorelabel notes the matching undo command once the doctor sees the fix in place. At the end, the uninstaller lists those undo commands under "Steps you ran yourself during setup", so you can decide which ones to run.

> **Will I lose my exam history?**
> Yes. Your history, settings and sessions live in `.workspace/`, which the uninstaller removes. Copy `.workspace/history.jsonl` somewhere first if you want to keep it.

> **I deleted the repository folder before uninstalling. What now?**
> autorelabel keeps a rescue copy of the uninstaller, with its ledger, in the lab storage subfolder. Run it from there:
>
> ```bash
> bash ~/.local/share/autorelabel/uninstall.sh --dry-run
> bash ~/.local/share/autorelabel/uninstall.sh
> ```
>
> (Replace `~/.local/share` with your lab storage directory if you chose another.)

The uninstaller is plain bash, on purpose: it works even when Python or the private environment is broken.
