# Changelog

Changes to the program, newest first. Planned versions are in [ROADMAP.md](ROADMAP.md).

Versions follow [semantic versioning](https://semver.org): a patch release (1.0.1) only fixes things, a minor release (1.1.0) adds something without breaking what you use, and a major release (2.0.0) may change how things work. The website and documentation aren't versioned. Check yours with `./autorelabel --version`.

## 1.4.0 (2026-11-14)

### Added

- **The Exam Desk: the exam in your browser.** Press `w` on the exam screen, or run `./autorelabel desk`. It shows:
  - the tasks on the left, with done and review marks;
  - a terminal or the serial console to every node on the right, one or two side by side;
  - the clock on top, with warnings at 15 and 5 minutes, and reset node and end exam, each with a confirmation.

  Your shells survive a closed or reloaded tab. At time up the terminals become read-only, and that is enforced by autorelabel, not by the page. Full screen hands Ctrl+W, Ctrl+T and Ctrl+N to your shell in Chrome, Chromium and Edge. The text interface keeps working beside it.
- It is reachable only from your own computer, by your own user, and only from its own page. It opens after you type a code that autorelabel shows you, and it keeps no cookie. The [security guide](https://autorelabel.dpdns.org/docs/security/) has the details.

## 1.3.1 (2026-11-14)

### Changed

- **Installing takes less typing.** If Python's `venv` module is missing, `./autorelabel` now offers to install it with the one command for your distribution, and carries on. Together with **Fix for me** on the host check, which installs Vagrant, Packer and libvirt for you, you only need `git` and three commands to start.
- The results dashboard's exam filter is now matched against a fixed list in a way code scanning can follow. It was already limited to RHCSA and RHCE.

### Fixed

- **Fix for me** no longer starts the VirtualBox step where VirtualBox comes from Oracle's download page (Debian, Ubuntu, Fedora and RHEL families). It used to add you to the `vboxusers` group, which fails until VirtualBox is installed, and stop there. The step is now listed for you, with the download page.

## 1.3.0 (2026-11-13)

### Added

- **The results dashboard: your graded attempts in the browser.** Start it with `./autorelabel dashboard`, or press **o** on **Progress and history** in the text interface. It shows:
  - your scores over time against the pass mark: point at a result for its details, select it for its report;
  - the objectives that keep costing you points;
  - the checks you failed more than once;
  - the answers that worked before the grading reboot and not after it;
  - every objective of the exam, tested or not, with your share of its points and its trend;
  - every task you have met, with each of its checks;
  - each attempt's full report, every check before and after the reboot.

  You can count full exams only, or practice sets as well. It reads the files autorelabel already keeps and changes nothing.
- It runs on your computer only, at `127.0.0.1`, and loads nothing from the internet. The address it opens works once and only for your own user, it answers to no other host name, and its pages hold no script. The [security guide](https://autorelabel.dpdns.org/docs/security/) has the details.

### Fixed

- **Progress and history** in the text interface no longer stops at a damaged line in your attempt history.

## 1.2.0 (2026-11-13)

### Changed

- **Generated exams vary more.** Every exam still has 20 tasks worth 300 points and the same pass mark. What changed:
  - It now has one of three difficulty mixes: 6, 5 or 4 hard tasks, with medium tasks making up the rest.
  - The objective domains have wider ranges.
  - The generator plans ahead, so a task is no longer crowded out by the others.

  Before, 8 RHCSA tasks and 4 RHCE tasks came up in fewer than 3 exams in 100, some of them almost never. Now even the rarest task comes up in about 4 RHCSA exams in 100, or about 7 RHCE exams in 100.
- **Your last two exams are held back.** A task from your previous graded exam is much less likely to come up in the next one, and a task from the exam before that somewhat less. Measured over many exams in a row, an RHCSA exam now repeats about 2 of the previous exam's 17 drawn tasks, where it used to repeat 5. Practice sets don't count. Attempts graded before 1.1.1 don't record their tasks, so this starts with your first exam graded on 1.1.1 or later.
- A damaged line in your attempt history no longer stops a new exam from starting.
- The same seed gives a different exam than in 1.1, and it also depends on your last two exams. **Retake** still repeats an exam exactly.

### For contributors

- A blueprint may list `alternative_mixes`, and `bank lint` checks that every mix has the blueprint's task count and points.

## 1.1.1 (2026-11-13)

### Security

- **VirtualBox: the lab VMs could reach services that listen only on your computer's `127.0.0.1`.** The box build needs a VirtualBox NAT option for the installer, the finished box kept it, and every lab VM inherited it. So a program inside a VM could connect to `10.0.2.2` and reach, for example, a local database or development server. The option is now turned off in the box, in the lab, and before every VM start, which also covers labs built with 1.1.0: you don't need to rebuild anything. If VirtualBox refuses these settings for a VM, the VM isn't started, and you see what VirtualBox said. libvirt was never affected.
- RHCE: VS Code in the browser listens only inside the control node. Before, the other lab VMs and your computer could reach it at its lab address, protected by its password. You still open it at the same `127.0.0.1` address.
- RHCE: the Python packages for the control node are checked against recorded SHA-256 checksums, when they're downloaded and again when the lab installs them. Packages you downloaded with an earlier version stay valid.
- If your session has no `XDG_RUNTIME_DIR`, autorelabel keeps its sockets in `/tmp/autorelabel-<uid>`. It now refuses that folder if another user created it.

### Fixed

Correct answers that were marked wrong:

- RHCSA:
  - an ACL task where the writer was given `rwx` on the directory;
  - a sudo rule written without a run-as list (`%group ALL=ALL`);
  - the lab's time server in a `pool` line;
  - SSH key-only login set with `AuthenticationMethods publickey`;
  - an NFS mount with `x-systemd.automount`;
  - fstab entries with a trailing slash or the type `auto`;
  - a crontab with day names;
  - other valid SELinux types for web content.
- RHCSA: tasks that were graded against the system at grading time, not as it was when you answered:
  - the manual page search: a package installed later added pages;
  - the bzip2 archive: files were added to the directory later;
  - the saved log messages: the service was restarted later;
  - the sudo log entry: the log was rotated.
- RHCSA: two tasks failed whenever any unit on the node had failed, even one that belonged to another task.
- RHCE:
  - a package task with `name` given as a list;
  - the SELinux system role under its `linux-system-roles` name;
  - an `at` job queued hours before grading, in a session that was paused and resumed.

Grading and the exam:

- Grading waits for a node to finish booting before it runs the checks after the reboot. Before, a slow service could be checked while it was still starting.
- A node that refuses to reboot is restarted through the hypervisor at once. A boot that is slow but still moving gets more time before the node is given up.
- "The grader cannot reach nodeX" now also arrives as a desktop notification, and a node that is simply rebooting no longer counts as an incident.
- When grading resumes a paused lab, it sets the VMs' clocks from your computer. Before, they could keep the time at which they were paused.
- A mark you set on a task while the proctor was saving could be lost. Sessions are now saved under a lock.
- libvirt: when Vagrant gave up on a VM that was still booting, the lab build failed. The retry meant for that case now happens.
- The security guide said the lab VMs can't reach your computer. They can, at its address on the lab networks. The guide now says so, and says what VirtualBox's NAT adapter does and does not keep out.

### Changed

- Each graded attempt records which tasks it had. Nothing uses it yet; later versions will.

### For contributors

- Self-test records hold digests of the lab's provisioning, the box build and the check libraries. `selftest --stale` re-runs what was tested before one of them changed, and a release tag is refused while such a record is left.
- A task can set `selftest_alone: true` when one of its tests would destroy what other tasks in the batch hold.
- Checks get `AR_STARTED`, the session's start time.
- CI installs its lint, test and Ansible tools from hash-locked files, and CodeQL scans the Python code, the website's scripts and the workflows.

## 1.1.0 (2026-11-04)

### Added

- `./autorelabel doctor --fix`, and **Fix for me** (`f`) in the text interface's host check, install what the doctor found missing. They show every command with its undo command and ask once, then run the commands in your terminal, so `sudo` asks for your password itself. The run stops at the first command that fails. Only commands tested for your distribution family are run; steps such as Vagrant from the AUR stay yours to do.
- The box build checks the RHEL ISO against the SHA-256 checksums Red Hat publishes for the RHEL 10.0 and 10.2 x86_64 DVDs. A damaged download stops the build before the installer starts, not 10 minutes into it. For other versions the checksum is shown so you can compare it with Red Hat's download page. `box status` shows when the ISO was verified.

### Changed

- Packer plugins are pinned to exact versions (qemu 1.1.7, virtualbox 1.1.5, vagrant 1.1.7), so a new plugin release can't change the box until it has been tested.

### Fixed

- On Debian and Ubuntu, adding HashiCorp's repository no longer stops to ask "Overwrite?" when its key is already installed.

## 1.0.1 (2026-11-04)

### Fixed

- Text in the text interface's dialogs wraps to the dialog's width. Before, the welcome, RHCE download and uninstall dialogs broke lines in the middle of sentences, leaving one or two words on a line of their own.

## 1.0.0 (2026-10-25)

The first release: RHCSA and RHCE practice exams on RHEL 10, graded after a reboot. The [release notes](https://github.com/syed-913/autorelabel-rhcsa-rhce/releases/tag/v1.0.0) list what it does.
