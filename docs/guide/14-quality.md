# How the tasks are tested

A practice exam is only useful if its grading is right. Every task in autorelabel is tested on real RHEL 10 virtual machines before it ships, and this page shows where those tests stand today.

## What a self-test checks

Each task is run in a fresh lab, and graded after a reboot, the same way your exam is:

- **The untouched lab scores 0.** A task that gives points for doing nothing is broken.
- **The reference solution scores full marks.** It's the one you see in practice mode and after grading.
- **Every accepted alternative scores full marks.** If the exam allows two ways to do something, such as `nmcli` and a keyfile, both are tested.
- **Every classic mistake loses points.** A firewall rule without `--permanent`, `chcon` in place of `semanage fcontext` or a vault file left unencrypted must not score full marks.

Many tasks draw random details, such as a user name, a port or a size. The sweep tests every possible value of each detail at least once, so no draw of the exam can be ungradeable.

## Where the tests stand

<!-- quality:start -->
| | RHCSA (EX200) | RHCE (EX294) |
|---|---|---|
| **Tasks** | 102 (2 practice-only) | 55 |
| **Objective lines** | 62, each practised by 2 or more tasks | 57, each practised by 2 or more tasks |
| **Accepted alternatives tested** | 23 | 12 |
| **Classic mistakes tested** | 118 | 63 |
| **Self-tested on libvirt/KVM** | 102 of 102 on their current files, RHEL 10.0, on 2026-10-19 | 55 of 55 on their current files, RHEL 10.0, 2026-10-20 to 2026-10-25 |
| **Self-tested on VirtualBox** | 102 of 102 on their current files, RHEL 10.0, 2026-10-19 to 2026-10-25 | 55 of 55 on their current files, RHEL 10.0, 2026-10-24 to 2026-10-25 |
| **Tasks with random details** | 59: 204 of 204 draws passed | 32: 106 of 106 draws passed |
<!-- quality:end -->

The table is generated from the self-test records in the repository. Each record holds a fingerprint of the task's files, and a task counts as tested only while its files still match it. When a task is edited, the repository's checks fail until it has been tested again on both hypervisors.

> **I think a task grades me unfairly. What should I do?**
> Please [send task feedback](https://github.com/syed-913/autorelabel-rhcsa-rhce/issues/new?template=task-feedback.yml) with the task's name and what you did. You can see the [open task feedback](https://github.com/syed-913/autorelabel-rhcsa-rhce/issues?q=is%3Aissue+is%3Aopen+label%3Atask-feedback) too. Every fix is self-tested again before it ships.
