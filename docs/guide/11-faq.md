# FAQ

## About the project

### Is there a free RHCSA practice exam for RHEL 10?

Yes, this project. autorelabel generates timed RHCSA (EX200) exams from a bank of 102 tasks that covers every current objective, runs them on real RHEL 10 virtual machines, and grades them automatically after a reboot. It is free and open source under the MIT License.

### Is there an RHCE practice exam for RHEL 10 and Ansible?

Yes. RHCE (EX294) exams use 55 tasks, `ansible-core` 2.16 and the RHEL system roles from the RHEL 10 DVD, and `ansible-navigator` with an execution environment, as the current objectives require. VS Code runs in your browser with Red Hat's Ansible extension, for the objectives about the editor.

### Are these real exam questions?

No. Every task was written from the objectives Red Hat publishes on the [EX200](https://www.redhat.com/en/services/training/ex200-red-hat-certified-system-administrator-rhcsa-exam) and [EX294](https://www.redhat.com/en/services/training/ex294-red-hat-certified-engineer-rhce-exam-red-hat-enterprise-linux) exam pages and from Red Hat's public documentation. The project contains no real exam content, and it isn't affiliated with or endorsed by Red Hat. [COVERAGE-RHCSA.md](../COVERAGE-RHCSA.md) and [COVERAGE-RHCE.md](../COVERAGE-RHCE.md) show which objective each task comes from.

### Does it cover the new RHEL 10 objectives, like Flatpak and systemd timers?

Yes. The bank follows the current objective pages word for word, including Flatpak repositories and applications, systemd timer units, and the RHCE objectives about VS Code and `ansible-navigator`. The full list is on the [objectives page](12-objectives.md).

### How close is the grading to Red Hat's?

Red Hat doesn't publish how its grader works. autorelabel follows what is known: your systems are rebooted, only persistent configuration counts, and the checks look at the final state, never at the commands you typed. It gives partial credit per check by default, and you can switch to all-or-nothing in Settings. See [Grading and results](05-grading-and-results.md).

### How do I know the tasks are correct?

Every task is self-tested on real RHEL 10 VMs, on both libvirt and VirtualBox, before it ships. The untouched lab must score 0, the reference solution and every accepted alternative must score full marks, and the classic mistakes must lose the points they should. For tasks with random details, every possible value of each detail is tested at least once. If you still find a task that grades you unfairly, please [report it](09-troubleshooting.md#problem-reports).

## Requirements

### Do I need a Red Hat subscription?

No. You need a free Red Hat Developer account to download the RHEL 10 ISO, and that is all. The box is installed offline from the DVD and is never registered.

### Can I use AlmaLinux or Rocky Linux in place of RHEL?

Not in this version. The exam is on RHEL 10, so the lab is too, and the tasks are tested against RHEL 10 itself. Your computer itself can run any of the supported Linux distributions, including AlmaLinux and Rocky Linux.

### Does it work on Windows or macOS?

Not yet. autorelabel needs a Linux x86_64 computer. Windows support (with VirtualBox) is planned for version 2. WSL isn't supported, because nested virtualization and networking are unreliable there.

### How much memory and disk space do I need?

About 3 GB of free RAM for an RHCSA exam with the *lite* profile, and about 5.5 GB for RHCE. About 30 GB of free disk (40 GB for RHCE), in the folder you choose. See the table in [Installing](01-installing.md#3-setup-three-questions).

### Does it need the internet?

Only for downloads, and only once each: autorelabel's Python libraries on the first run, Packer's plugins when the box is built, and the RHCE content before the first RHCE exam. The lab itself is always offline, like the real exam.

### Does it send any data anywhere?

No. There is no telemetry and no account. A problem report only reaches the project if you post it yourself.

## Using it

### How do I practise for the RHCSA on RHEL 10 at home?

Install libvirt (or VirtualBox), download the RHEL 10 DVD with a free developer account, clone this repository and run `./autorelabel`. The README's [Requirements](../../README.md#requirements) section has the exact commands for your distribution, and [Your first exam](02-first-exam.md) shows what follows.

### I can't log in to node1. What is the password?

It is in the instructions shown before the exam: press `i` on the exam screen, or run `./autorelabel exam tasks`. The console prints it when you connect to node1, and console-only tasks show it under their text. node2's root password is the only one that is unknown, because resetting it is one of the tasks.

### Will I get the same tasks every time?

No. Each exam draws 20 tasks within a fixed blueprint (6 easy, 8 medium and 6 hard), randomises their details, and favours objectives you haven't practised recently. To repeat an exam exactly, use **Retake** on its results screen.

### Can I pause an exam?

Not on purpose, just as in the real exam. If your computer sleeps, crashes or restarts, that time isn't counted (with the default settings), and you can resume where you were.

### Can I take an exam without the text interface?

Yes. Every step has a command: `./autorelabel exam start rhcsa`, `exam tasks`, `ssh`, `console`, `exam submit`, `exam results`. See the [command reference](07-commands.md).

### Why is the project called autorelabel?

After resetting a forgotten root password with `rd.break`, you must create the file `/.autorelabel` so SELinux relabels the file system on the next boot. Forget it, and the node won't let anyone log in. It is one of the most famous ways to lose points on the RHCSA, and after one exam here you won't forget it again.

## Contributing

### Can I write tasks?

Yes. [TASK-AUTHORING.md](../TASK-AUTHORING.md) explains the format, the rules every task follows (sources, traceability from requirements to checks, wording) and the self-tests a task must pass. [ARCHITECTURE.md](../ARCHITECTURE.md) describes how the rest fits together.

### Where do I report a bug or a wrong task?

On the [issue tracker](https://github.com/syed-913/autorelabel-rhcsa-rhce/issues/new/choose), which has a form for each case. For failures, the **Problem report** form asks for the report autorelabel writes; see [Troubleshooting](09-troubleshooting.md#problem-reports). For a task that is unclear, or that marked a correct solution as wrong, use **Task or grading feedback**. Questions and ideas go to [Discussions](https://github.com/syed-913/autorelabel-rhcsa-rhce/discussions), and security problems to the private form described in [SECURITY.md](../../SECURITY.md).
