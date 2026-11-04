# Changelog

Changes to the program, newest first. Planned versions are in [ROADMAP.md](ROADMAP.md).

Versions follow [semantic versioning](https://semver.org): a patch release (1.0.1) only fixes things, a minor release (1.1.0) adds something without breaking what you use, and a major release (2.0.0) may change how things work. The website and documentation aren't versioned. Check yours with `./autorelabel --version`.

## 1.0.1 (2026-11-04)

### Fixed

- Text in the text interface's dialogs wraps to the dialog's width. Before, the welcome, RHCE download and uninstall dialogs broke lines in the middle of sentences, leaving one or two words on a line of their own.

## 1.0.0 (2026-10-25)

The first release: RHCSA and RHCE practice exams on RHEL 10, graded after a reboot. The [release notes](https://github.com/syed-913/autorelabel-rhcsa-rhce/releases/tag/v1.0.0) list what it does.
