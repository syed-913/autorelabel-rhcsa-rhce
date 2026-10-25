# Grading and results

autorelabel grades the way Red Hat describes its performance-based exams: your systems are rebooted, and only what persists counts. It looks at the final state of your systems, never at the commands you typed. This page explains what happens from the moment the exam ends, how the points are calculated, and how to read the results.

## When grading starts

Grading starts when the time runs out or when you submit. First the lab is **frozen**: every VM is paused, so nothing can change any more, and in an RHCE exam the VS Code forwarding is closed. The proctor then grades the exam in the background. If autorelabel is open you watch it happen on the grading screen; if it isn't, the results are waiting for you the next time you open it.

> **Can grading be interrupted?**
> It can be, by a crash or a power cut, but nothing is lost. Grading saves its progress after every single check, and the next time you open autorelabel it continues exactly where it stopped. The home screen shows **Finish grading** in that case.

## The three phases

### 1. Checking your work before the reboot

Every check of every task runs once while the nodes are still as you left them. **This pass earns no points.** It exists only to compare with phase 3, so that work which disappears with the reboot can be pointed out.

### 2. Rebooting every exam node

Each node is rebooted from inside with `systemctl reboot`, the same clean reboot you would do. autorelabel then waits for the node to go down and come back with a new boot ID. If something gets in the way, it escalates step by step, the way a person at the console would:

- A node that doesn't shut down within 90 seconds gets an ACPI power-button press.
- A node still running 60 seconds after that is hard-reset. This is recorded with a hint, because the usual cause is a hung NFS mount without `_netdev`, or a service that won't stop.
- A node that was already unreachable before the reboot (emergency mode, a broken network) first gets `Ctrl+Alt+Del`, which asks systemd for a clean reboot.

Each node then has 5 minutes to come back. If its serial console shows that SELinux is relabelling the file system, which is normal after a root password reset, it gets 15 more minutes.

> **What happens if a node doesn't come back?**
> autorelabel reads the node's serial console and tells you why, in plain words. Its checks can't run, so the tasks on that node score 0, as they would in the real exam. The diagnoses it can give are:
>
> | What the console shows | What it usually means |
> |---|---|
> | Emergency mode ("Give root password for maintenance") | A bad `/etc/fstab` entry, or a volume that doesn't exist |
> | A `grub>` prompt | The boot loader configuration is broken |
> | A kernel panic | Wrong kernel arguments, or a wrong root device |
> | A login prompt, but SSH fails | Locked out: `sshd`, PAM, the `vagrant` account, `mgmt0`, or wrong SELinux labels on files like `/etc/shadow` |
> | Still booting after the time allowed | Something at boot takes far too long |

### 3. Grading after the reboot

Every check runs again on the rebooted nodes. **This is the pass that counts.**

## How the points are calculated

Every task is worth 10 (easy), 15 (medium) or 20 (hard) points, and it is graded by several checks. Each check tests one requirement of the task, for example "the service is enabled at boot" or "port 8909 has the `http_port_t` label".

With **partial scoring**, the default, a task earns the share of its points that matches the share of its checks that pass. Checks can carry different weights; most carry the same.

> **Why did I get 13.33 out of 20?**
> Because two of the task's three checks passed after the reboot, and two thirds of 20 is 13.33. The results screen shows exactly which check failed.

With **strict scoring**, each task is all or nothing: every check must pass, or the task scores 0. You can switch in [Settings](08-settings.md). Strict is the harsher rule, and some people use it to practise with a safety margin.

> **What is a "guard" check?**
> A check that something you must *not* break is still fine: SELinux stays enforcing, existing data is still there, SSH is still allowed. A guard is already true before you start, so a task earns nothing until at least one of its other checks passes. After that, guards count like every other check, so breaking one still costs points. The results label guards so you know why one passed on an untouched task.

> **Does the method I use matter?**
> No. The checks look only at the result. A file system can be mounted by UUID or by label, a connection can be made with `nmcli` or by writing a keyfile, a partition with `parted` or `fdisk`. Every accepted alternative was run through the grader on real VMs before the task was released.

## Persistence warnings

When a check **passed before the reboot but failed after it**, the results add the note **worked before the reboot, not after: not persistent**. Your work was right, but it lived only in memory. These are the classic causes:

| Change that doesn't survive a reboot | The persistent way |
|---|---|
| `firewall-cmd --add-port=…` | add `--permanent` (and reload), or run `firewall-cmd --runtime-to-permanent` |
| `setenforce 1` | also set `SELINUX=enforcing` in `/etc/selinux/config` |
| `mount /dev/… /mnt/…` | add the file system to `/etc/fstab` |
| `systemctl start …` | `systemctl enable --now …` |
| `hostname new-name` | `hostnamectl set-hostname new-name` |
| `ip addr add …` | an `nmcli` connection with `connection.autoconnect yes` |
| `sysctl -w …` | a file in `/etc/sysctl.d/` |

## The results screen

- **Score** out of 300, with **PASS** or **FAIL** against the pass mark of 210.
- **By difficulty:** points earned out of points possible for easy, medium and hard tasks.
- **By domain:** the same for each objective domain, such as "Manage security".
- **Incidents:** anything unusual that happened to a node, explained in one line (see below).
- **The task list:** ✔ for full points, ◐ for partial points, ✘ for none.
- **The selected task's checks:** each with ✔ or ✘, a short detail for failed checks, and the persistence note where it applies.

| Key | What it does |
|---|---|
| `v` | The selected task's solution: a step-by-step answer with references to Red Hat's documentation. |
| `t` | Retake the same exam: same tasks, same details, back to the exam's starting point. |
| Escape | Back to the home screen. |

> **What are the incidents in my results?**
> Events that affected a node, recorded so you can understand your score. For example: the node was powered off at grading time and was powered on; it didn't shut down and was hard-reset; it had to be restarted during the reboot; you used *Reset to exam start* on it; or the grader lost access to it during the exam. Incidents don't cost points by themselves.

## Where the results are kept

Each session has its own folder, `.workspace/sessions/<session>/`, with `results.json` (everything above, machine-readable) and `report.md` (a readable report). Every graded attempt is also added to `.workspace/history.jsonl`, which the **Progress and history** screen reads to show your scores over time and your weakest objectives.

From the command line:

```bash
./autorelabel exam results              # the latest graded report
./autorelabel exam results --solutions  # the report followed by every solution
```

> **How close is this to Red Hat's real grading?**
> Nobody outside Red Hat knows exactly how the real exam scores each task. autorelabel follows what Red Hat does say about it: your systems are rebooted, and only configuration that persists counts. Partial scoring is the default here, and strict scoring is there if you prefer to practise against a harder rule.
