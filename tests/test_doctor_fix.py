"""doctor --fix runs only tested commands, each once, in order, and stops at the first failure."""

from __future__ import annotations

import pytest

from autorelabel import cli, config, doctor
from autorelabel.doctor import Check, Status


def _checks(tmp_path) -> list[Check]:
    log = tmp_path / "ran"
    repo = f"echo repo >> '{log}'"
    return [
        Check("platform", "Linux host", Status.OK),
        Check("vagrant", "Vagrant", Status.FAIL, fix=["# Vagrant", repo, f"echo vagrant >> '{log}'"],
              undo=["sudo apt remove vagrant"], fixable=True),
        Check("packer", "Packer", Status.FAIL, fix=["# Packer", repo, f"echo packer >> '{log}'"], fixable=True),
        Check("aur", "Vagrant (AUR)", Status.FAIL, fix=["# install it from the AUR"], fixable=True),
        Check("virtualbox", "VirtualBox", Status.FAIL, fix=["sudo modprobe -r kvm"]),     # situational
        Check("subnets", "Lab subnets", Status.WARN, fix=["# choose different subnets in Settings"]),
    ]


def test_plan_runs_tested_commands_and_leaves_the_rest_to_you(tmp_path, monkeypatch):
    monkeypatch.setattr("autorelabel.guides.family", lambda *_a: "debian")
    run, manual = doctor.fix_plan(_checks(tmp_path))
    assert [c.id for c in run] == ["vagrant", "packer"]
    assert [c.id for c in manual] == ["aur", "virtualbox", "subnets"]


def test_unknown_distributions_get_no_automatic_fixes(tmp_path, monkeypatch):
    monkeypatch.setattr("autorelabel.guides.family", lambda *_a: "generic")
    run, manual = doctor.fix_plan(_checks(tmp_path))
    assert run == [] and len(manual) == 5


def test_commands_run_in_order_and_shared_steps_once(tmp_path, monkeypatch):
    monkeypatch.setattr("autorelabel.guides.family", lambda *_a: "debian")
    run, _ = doctor.fix_plan(_checks(tmp_path))
    assert doctor.apply_fixes(run, write=lambda _s: None)
    assert (tmp_path / "ran").read_text().split() == ["repo", "vagrant", "packer"]


def test_the_first_failure_stops_the_run(tmp_path):
    log = tmp_path / "ran"
    plan = [Check("a", "A", Status.FAIL, fix=["false | true"], fixable=True),       # pipefail catches it
            Check("b", "B", Status.FAIL, fix=[f"echo b >> '{log}'"], fixable=True)]
    out: list[str] = []
    assert not doctor.apply_fixes(plan, write=out.append)
    assert not log.exists() and "false | true" in out[-1]


@pytest.fixture()
def fix_cli(tmp_path, monkeypatch):
    monkeypatch.setattr("autorelabel.guides.family", lambda *_a: "debian")
    monkeypatch.setattr(doctor, "run", lambda *_a, **_k: [])
    return config.Settings(), _checks(tmp_path)


def test_fix_needs_a_terminal(fix_cli, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert cli._doctor_fix(fix_cli[0], "rhcsa", fix_cli[1]) == 2


def test_nothing_runs_without_a_yes(fix_cli, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _p: "")
    assert cli._doctor_fix(fix_cli[0], "rhcsa", fix_cli[1]) == 1
    assert not (tmp_path / "ran").exists()
    out = capsys.readouterr().out
    assert out.count("echo repo") == 1 and "sudo apt remove vagrant" in out and "Nothing was run" in out
