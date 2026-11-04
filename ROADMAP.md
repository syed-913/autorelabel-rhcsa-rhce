# Roadmap

What each coming version is planned to contain, and where it stands. When a version is released, its entry moves to the [changelog](CHANGELOG.md). Plans change as people use the labs; the order below is the current one, not a promise of dates. Ideas and requests are welcome in [Discussions](https://github.com/syed-913/autorelabel-rhcsa-rhce/discussions).

| Version | Theme | Status |
|---|---|---|
| 1.0.1 | Dialog text wrapping | released |
| 1.1.0 | Setup and verification | in progress |
| 1.1.x | Fixes from real exam attempts | as reports come in |
| 1.2.0 | Terminals in your browser | planned |
| 1.3.0 | Results dashboard | planned |
| 2.0.0 | Windows | planned, needs testing first |
| later | More Red Hat exams | ideas |

## 1.1.0: setup and verification

- [ ] **`./autorelabel doctor --fix`** installs the missing host packages for your distribution. It is opt-in: it shows every command first, asks once, and runs them through `sudo`, which asks for your password itself. It stops at the first failure and never installs from the AUR or from unknown sources.
- [ ] **The RHEL ISO is checked against Red Hat's published SHA-256 checksums** before the box is built. A download that doesn't match the checksum Red Hat publishes for its version stops the build with a clear message, instead of failing 10 minutes later inside the installer.
- [ ] **Packer plugins pinned to exact versions**, so every box is built with the same plugins.

## Alongside 1.1.0 (repository and website, not versioned)

- [ ] GitHub Actions pinned to commit SHAs, kept current by Dependabot.
- [ ] A GitHub release is created from this changelog when a version tag is pushed.
- [ ] Signed release tags.
- [ ] [OpenSSF Scorecard](https://scorecard.dev) on the repository.
- [ ] A CI check that every task has passing self-tests on both hypervisors for its current files, so an edited task can't ship untested.
- [ ] A monthly check of Red Hat's EX200 and EX294 objective pages that opens an issue when the objectives change.
- [ ] Website: a page on security and what autorelabel does to your computer, "Will it run on my computer?", the distributions it supports by name, an updated comparison, a new demo video, and its own domain.

## 1.1.x: fixes from real exam attempts

Patch releases for whatever real attempts turn up, starting with the maintainer's own RHCSA. Report problems with the [issue forms](https://github.com/syed-913/autorelabel-rhcsa-rhce/issues/new/choose).

## 1.2.0: terminals in your browser

`./autorelabel web` opens the lab in your browser on `127.0.0.1`: a terminal for each node, the serial console (for `rd.break` and GRUB), and VS Code for RHCE, side by side. The text interface stays where you start, submit and review exams. Closing or refreshing the tab doesn't lose your shells. Typing has to feel as fast as a native terminal; that is tested, not assumed.

## 1.3.0: results dashboard

A read-only page that shows your scores over time, your weakest objectives, and every check of every attempt, from the files autorelabel already keeps. Works offline.

## 2.0.0: Windows

The plan is to run autorelabel inside WSL2 on Windows 11, which can run KVM itself, so the lab works as it does on Linux. Native VirtualBox stays the fallback for Windows 10. This needs testing on real Windows machines before anything is promised.

## Later: more Red Hat exams

Any new exam has to keep the same promise: built from your own RHEL DVD, runs offline on a laptop, no paid subscription, graded from the final state after a reboot. EX342 (diagnostics and troubleshooting) fits best and comes first.
