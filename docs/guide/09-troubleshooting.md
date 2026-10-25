# Troubleshooting

When something doesn't work, start with the doctor. It checks everything autorelabel depends on and prints the exact commands for your distribution:

```bash
./autorelabel doctor
```

The same check is on the home screen (**Doctor**, or press `d`). It never changes anything on your computer; it shows you what to run.

## The doctor's checks

| Check | What it looks at | If it fails |
|---|---|---|
| **Linux host** | That this is Linux on x86_64, not WSL. | Windows support is planned for v2; WSL and macOS aren't supported. |
| **CPU supports RHEL 10** | The x86-64-v3 instruction set that RHEL 10 requires, and hardware virtualization (VT-x or AMD-V). | A missing instruction can't be fixed; RHEL 10 won't boot on that CPU. Missing virtualization usually means it is turned off in the BIOS/UEFI. |
| **/dev/kvm available** | That KVM exists and your user can open it. | Enable virtualization in the BIOS/UEFI, or add yourself to the `kvm` group and log in again. |
| **OpenSSH client** | That `ssh` is installed. | Install it with the command shown. |
| **Vagrant**, **Packer** | That they are installed, in version 2.3+ and 1.10+. | Install or update them with the commands shown. |
| **libvirt** | That `virsh` can reach `qemu:///system`, and that `qemu-img` and QEMU are installed. | Install libvirt and start its service; on RHEL-family hosts, QEMU is `/usr/libexec/qemu-kvm`, which is accepted too. |
| **Member of the libvirt group** | That your user may manage system VMs. | Add yourself to the group, then **log out and back in**. "Added, but this login session predates it" means only the logging out is missing. |
| **vagrant-libvirt plugin** | That Vagrant can create libvirt VMs. | Install the plugin with the commands shown. |
| **VirtualBox** | The version (7.2.2 or newer), your `vboxusers` membership, and whether KVM is holding the CPU's virtualization (see below). | Follow the message. |
| **vagrant-registration plugin** | Information only: if you have it, autorelabel turns it off for its labs, so you are never asked for Red Hat credentials. | Nothing to do. |
| **Free memory** | Free RAM against what the lab needs, plus about 0.75 GB for your desktop. | Close other VMs or applications, or use the *lite* profile. A warning, not a blocker. |
| **Lab storage directory** | That it exists, is writable, is on a local disk (not tmpfs, NFS or SMB), has enough free space, and that the VM user can reach it. | Choose another folder, free some space, or run the `setfacl` commands shown (explained in [Installing](01-installing.md#4-building-the-box)). |
| **RHEL 10 DVD ISO** | That the file is a RHEL 10 DVD (not the boot ISO) and that the VM user can read it. | Download the right image, or run the `setfacl` commands shown. |
| **Lab networks don't collide** | That the lab and management subnets don't overlap a network your computer uses. | Pick other subnets in [Settings](08-settings.md). |
| **RHEL 10 box** | Whether the box is built. | Information only: it is built at setup, or with `./autorelabel box build`. |
| **No VMs running under the other hypervisor** | That no VirtualBox VMs run while libvirt is in use, or the other way round. | Shut the other hypervisor's VMs down. |
| **VirtualBox free for the lab profile** | That VirtualBox Manager and your own VirtualBox VMs are closed (VirtualBox only). | Close them; see below. |
| **Host footprint** | Information only: what autorelabel has created so far, for the uninstaller. | Nothing to do. |

## Common problems

| Problem | What to do |
|---|---|
| **I don't know node1's root password.** | It is in the instructions: press `i` on the exam screen, or run `./autorelabel exam tasks`. The console also prints it when you connect. Only node2's password is unknown in an RHCSA exam, on purpose. |
| **SSH to node1 doesn't work at the start.** | Expected: node1 has no network until you configure it. Use the console (`c` on the exam screen, or `./autorelabel console node1`). |
| **The console shows nothing.** | Press Enter. A serial console only prints when something writes to it. |
| **My computer crashed, rebooted or slept during an exam.** | Open `./autorelabel`. It notices and offers to resume. The time it was off isn't counted (unless you turned off *Forgive host downtime*). |
| **A node hangs, or I powered it off.** | Select it on the exam screen, press `n`, and choose **Reset** or **Power on**. |
| **I broke a node completely.** | Press `n` and choose **Reset to exam start**. All your work on that node is lost; your other nodes are not touched. |
| **The exam screen says the grader can't reach a node.** | Undo your last change to `mgmt0`, the `vagrant` account, `sshd` or sudo on that node. See [The exam screen](03-exam-screen.md#the-warning-banner). |
| **A node didn't come back after the grading reboot.** | The results tell you what its console showed, such as emergency mode from a bad `/etc/fstab` line. That node scores 0, as in the real exam. Read the solution to see what persisted wrongly. |
| **Preparing the lab failed.** | The screen shows the error and offers **Retry**. The home screen also offers **Retry preparing the lab** later. If it keeps failing, autorelabel writes a problem report (below). |
| **The box build failed.** | Read the error and its hint. The full log is in `.workspace/logs/`. Building again usually helps after a temporary problem, such as a failed download. |

## VirtualBox and KVM on the same computer

You can have both installed, but they can't run VMs at the same time. Recent Linux kernels (6.12 and newer) load KVM in a way that keeps the CPU's virtualization switched on for KVM, and on some combinations of kernel and VirtualBox versions this freezes every KVM guest (the kernel log shows `kvm_intel: vmwrite failed`). autorelabel checks for running VMs of the other hypervisor before it starts a lab and tells you which ones to shut down.

If the doctor says **"KVM holds VT-x"**, VirtualBox VMs won't start at all. The message gives three ways out: use the libvirt provider; use VirtualBox 7.2.2 or newer on kernel 6.16 or newer, which can share the CPU with KVM; or reboot with the kernel option `kvm.enable_virt_at_load=0`.

> **Why must VirtualBox Manager be closed?**
> autorelabel keeps its VMs in a separate VirtualBox profile, so they never mix with your own VMs. VirtualBox serves only one profile at a time per user, so while VirtualBox Manager or one of your own VMs is running, the lab's profile can't be used. autorelabel waits briefly, then tells you what is still open. To look at the lab's VMs in the VirtualBox window (with Manager closed first), run `VBOX_USER_HOME=<lab storage>/autorelabel/virtualbox/profile virtualbox`.

## Logs

Everything autorelabel does is logged in `.workspace/logs/` inside the repository:

- `autorelabel.log`: the application log (rotated, with secrets masked).
- One log per long operation, such as `…-box-build-libvirt.log` or `…-lab-up-rhcsa.log`, with the full output of Vagrant, Packer and the setup scripts.
- `proctor-<session>.log`: the proctor's output, when it runs without systemd. With systemd, read it with `journalctl --user -u autorelabel-proctor-<session>`. The proctor also writes to `autorelabel.log`.

For more detail, run a command with `--debug` before it, for example `./autorelabel --debug doctor`. With `AUTORELABEL_DEBUG=1`, a box build also writes Packer's detailed log.

## Problem reports

When something fails that autorelabel can't fix by itself (a tool on your computer changed, a VM won't start, a task's setup fails), it writes a **problem report** and tells you where it is. Problems you can fix yourself, like a missing package, don't produce a report; the message tells you what to do.

A report is a Markdown file in `.workspace/reports/`. It contains:

- what failed, and the hint that was shown,
- the versions of autorelabel, your distribution, kernel and Python, and every tool and plugin,
- the doctor's checks,
- the error's traceback and the end of the relevant log.

Before anything is written, your home folder, user name and host name are replaced with placeholders, and passwords are masked. Read the report before you share it.

To post it, open the [problem report form](https://github.com/syed-913/autorelabel-rhcsa-rhce/issues/new?template=problem-report.yml) on GitHub, paste the report, and say what you were doing. On the failure screen, **Copy problem report** puts it on your clipboard. You can also write a report yourself at any time:

```bash
./autorelabel report "the lab doesn't start after updating my kernel"
```

> **Does autorelabel send reports, or anything else, by itself?**
> No. Nothing is ever sent anywhere automatically: there is no telemetry. autorelabel only goes online to download its Python libraries (first run), Packer's plugins (box build) and the RHCE content (first RHCE exam). A problem report reaches the project only if you post it yourself.
