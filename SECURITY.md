# Security policy

## Supported versions

Only the latest release gets fixes. When a problem is fixed, it goes out as a patch release (for example 1.0.1), and the release notes say what changed.

## Reporting a problem

Please don't open a public issue for a security problem. Report it privately on the [Security tab](https://github.com/syed-913/autorelabel-rhcsa-rhce/security/advisories/new) of this repository. Only the maintainer can see the report.

A useful report says what you found, how to reproduce it, which version you used (`./autorelabel --version`) and which hypervisor. You'll get an answer within a week. If the problem is confirmed, it is fixed in a patch release, and you are credited in the release notes unless you prefer not to be.

## What counts as a security problem

autorelabel runs on your computer with your user's rights, and never with `sudo`. These are the parts where a mistake would matter most:

- **The uninstaller** removes only what its ledger recorded. Removing anything else, or anything outside the folders described in [Files and uninstalling](docs/guide/10-files-and-uninstall.md), is a security problem.
- **The lab** is reachable only from your own computer, and VS Code in the browser (RHCE) listens only on `127.0.0.1`, reached through SSH. A way for another computer on your network to reach a lab VM or VS Code is a security problem.
- **Files and commands** that autorelabel writes or runs on your computer: a way for a task, a bank file or a lab VM to run commands on your computer, or to write outside the repository and the lab storage folder.
- **Problem reports** hide your home directory, user name and host name, and mask passwords. A report that leaks any of them is a security problem.

These are not security problems:

- The lab VMs themselves. They are practice machines with known passwords, and many tasks are about breaking into them (resetting the root password, for example).
- Solutions being visible in the repository. They are there on purpose, for practice mode and for review after grading.
