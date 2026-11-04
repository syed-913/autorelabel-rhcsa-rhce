# Changelog

Changes to the program, newest first. Planned versions are in [ROADMAP.md](ROADMAP.md).

Versions follow [semantic versioning](https://semver.org): a patch release (1.0.1) only fixes things, a minor release (1.1.0) adds something without breaking what you use, and a major release (2.0.0) may change how things work. The website and documentation aren't versioned. Check yours with `./autorelabel --version`.

## 1.1.0 (2026-11-04)

### Added

- `./autorelabel doctor --fix`, and **Fix for me** (`f`) in the text interface's host check, install what the doctor found missing. They show every command with its undo command and ask once, then run the commands in your terminal, so `sudo` asks for your password itself. The run stops at the first command that fails. Only commands tested for your distribution family are run; steps such as Vagrant from the AUR stay yours to do.
- The box build checks the RHEL ISO against the SHA-256 checksums Red Hat publishes for the RHEL 10.0 and 10.2 x86_64 DVDs. A damaged download stops the build before the installer starts, instead of failing 10 minutes into it. For other versions the checksum is shown so you can compare it with Red Hat's download page. `box status` shows when the ISO was verified.

### Changed

- Packer plugins are pinned to exact versions (qemu 1.1.7, virtualbox 1.1.5, vagrant 1.1.7), so a new plugin release can't change the box until it has been tested.

### Fixed

- On Debian and Ubuntu, adding HashiCorp's repository no longer stops to ask "Overwrite?" when its key is already installed.

## 1.0.1 (2026-11-04)

### Fixed

- Text in the text interface's dialogs wraps to the dialog's width. Before, the welcome, RHCE download and uninstall dialogs broke lines in the middle of sentences, leaving one or two words on a line of their own.

## 1.0.0 (2026-10-25)

The first release: RHCSA and RHCE practice exams on RHEL 10, graded after a reboot. The [release notes](https://github.com/syed-913/autorelabel-rhcsa-rhce/releases/tag/v1.0.0) list what it does.
