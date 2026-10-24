"""Problem reports: what they hold, what they hide, and when they are written."""

from __future__ import annotations

import getpass
import re
import socket
from pathlib import Path

import pytest

from autorelabel import paths, report
from autorelabel.box import BoxError
from autorelabel.engine import EngineError
from autorelabel.fsutil import LockBusy
from autorelabel.lab import LabError
from autorelabel.session import UnknownSession


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "WORKSPACE", tmp_path)
    monkeypatch.setattr(paths, "LOGS", tmp_path / "logs")
    monkeypatch.setattr(paths, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(report, "_doctor", lambda exam: ["- ok: Vagrant: Vagrant 2.4.9"])
    (tmp_path / "logs").mkdir()
    return tmp_path


def test_sanitize_hides_home_user_host_and_secrets():
    home, user, host = str(Path.home()), getpass.getuser(), socket.gethostname()
    text = report.sanitize(f"{home}/lab/disk.qcow2 owner {user} on {host}; password=hunter2")
    assert home not in text and "~/lab/disk.qcow2" in text
    if len(user) >= 3:
        assert not re.search(rf"\b{re.escape(user)}\b", text)
    if len(host) >= 3:
        assert host not in text
    assert "hunter2" not in text


def test_user_situations_are_not_reported():
    assert not report.reportable(EngineError("cannot start from state graded", user_fixable=True))
    assert not report.reportable(LabError("cancelled", user_fixable=True))
    assert not report.reportable(BoxError("ISO not found", user_fixable=True))
    assert not report.reportable(LockBusy("busy"))
    assert not report.reportable(UnknownSession("no such session: x"))
    assert not report.reportable(KeyboardInterrupt())
    assert report.reportable(LabError("vagrant up failed for utility"))
    assert report.reportable(EngineError("setup of task 3 failed on node1"))
    assert report.reportable(KeyError("disk1"))


def test_bugs_are_described_with_their_type():
    assert report.describe(KeyError("disk1")) == "KeyError: 'disk1'"
    assert report.describe(LabError("provisioning control failed")) == "provisioning control failed"


def test_report_holds_error_environment_traceback_and_log(workspace):
    log = workspace / "logs" / "lab-up.log"
    log.write_text("\n".join(f"line {i}" for i in range(200)) + f"\nERROR: failed in {Path.home()}\n")
    try:
        raise LabError("provisioning control failed", "dnf could not reach the utility server", log)
    except LabError as exc:
        path = report.write("Bringing up the RHCE lab", str(exc), hint=exc.hint, log_file=log, exc=exc, exam="rhce")
    text = path.read_text()
    assert path.parent == workspace / "reports" and path.name.endswith("-provisioning-control-failed.md")
    assert "Bringing up the RHCE lab: provisioning control failed" in text
    assert "Hint shown: dnf could not reach the utility server" in text
    assert "autorelabel " in text and "exam rhce" in text and "Vagrant 2.4.9" in text
    assert "Traceback" in text and "line 199" in text and "line 100" not in text
    assert str(Path.home()) not in text


def test_a_broken_report_never_hides_the_error(workspace, monkeypatch):
    monkeypatch.setattr(report, "render", lambda *a, **k: 1 / 0)
    path = report.write("Grading", "boom")
    assert "Grading: boom" in path.read_text() and "report incomplete" in path.read_text()


def test_cli_reports_an_unexpected_error(workspace, monkeypatch, capsys):
    from autorelabel import cli

    def broken(_args):
        raise KeyError("disk1")

    parser = cli.build_parser
    monkeypatch.setattr(cli, "build_parser", lambda: _patched(parser(), broken))
    assert cli.main(["lab", "health", "rhcsa"]) == 1
    err = capsys.readouterr().err
    assert "error: KeyError: 'disk1'" in err and report.ISSUES_URL in err
    assert len(list((workspace / "reports").glob("*.md"))) == 1


def _patched(parser, fn):
    for action in parser._subparsers._group_actions:
        lab = action.choices["lab"]
        for sub in lab._subparsers._group_actions:
            sub.choices["health"].set_defaults(func=fn)
    return parser


def test_cli_does_not_report_the_users_situation(workspace, monkeypatch, capsys):
    from autorelabel import cli

    def locked(_args):
        raise EngineError("cannot grade from state graded", user_fixable=True)

    parser = cli.build_parser
    monkeypatch.setattr(cli, "build_parser", lambda: _patched(parser(), locked))
    assert cli.main(["lab", "health", "rhcsa"]) == 1
    assert report.ISSUES_URL not in capsys.readouterr().err
    assert not (workspace / "reports").exists()


def test_bootstrap_links_the_same_issue_form():
    boot = (paths.ROOT / "autorelabel").read_text()
    assert f'ISSUES_URL="{report.ISSUES_URL}"' in boot
    assert (paths.ROOT / ".github" / "ISSUE_TEMPLATE" / report.ISSUES_URL.rsplit("=", 1)[1]).exists()
