# Roadmap

What each coming version is planned to contain, and where it stands. When a version is released, its entry moves to the [changelog](CHANGELOG.md). Plans change as people use the labs; the order below is the current one, not a promise of dates. Ideas and requests are welcome in [Discussions](https://github.com/syed-913/autorelabel-rhcsa-rhce/discussions).

| Version | Theme | Status |
|---|---|---|
| 1.x | Fixes from real exam attempts | as reports come in |
| 2.0.0 | Windows | planned, needs testing first |
| later | More Red Hat exams | ideas |

## Repository and website (not versioned)

- [x] GitHub Actions pinned to commit SHAs, kept current by Dependabot.
- [x] A GitHub release is created from the changelog when a version tag is pushed.
- [x] Signed release tags, verified by the release workflow before it publishes (from 1.1.1).
- [x] CodeQL code scanning, and CI tools installed from hash-locked files.
- [x] [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/syed-913/autorelabel-rhcsa-rhce) on the repository.
- [x] A CI check that every task has passing self-tests on both hypervisors for its current files, so an edited task can't ship untested. Its results are on [How the tasks are tested](docs/guide/14-quality.md).
- [x] A monthly check of Red Hat's EX200 and EX294 objective pages that opens an issue when the objectives change.
- [x] Website: its own domain, a narrated film, a page on [security and your computer](docs/guide/13-security.md), "Will it run on my computer?", the distributions it supports by name, an updated comparison, a contact page, and larger text for reading.
- [ ] Website: a results page where people share how their exam went, counting failures as well as passes.

## 1.x: fixes from real exam attempts

Patch releases for whatever real attempts turn up, starting with the maintainer's own RHCSA. Report problems with the [issue forms](https://github.com/syed-913/autorelabel-rhcsa-rhce/issues/new/choose).

## 2.0.0: Windows

The plan is to run autorelabel inside WSL2 on Windows 11, which can run KVM itself, so the lab works as it does on Linux. Native VirtualBox stays the fallback for Windows 10. This needs testing on real Windows machines before anything is promised.

## Later: more Red Hat exams

Any new exam has to keep the same promise: built from your own RHEL DVD, runs offline on a laptop, no paid subscription, graded from the final state after a reboot. EX342 (diagnostics and troubleshooting) fits best and comes first.
