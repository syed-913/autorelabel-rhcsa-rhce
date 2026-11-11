"""The grading reboot. A node the grader cannot reach gets Ctrl+Alt+Del first and a hard reset
only if that does not bring it back (never in the middle of an SELinux relabel). A node that is
back is given time to finish booting before its checks run."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from autorelabel import console, grader, proc, remote
from autorelabel.grader import Grader


class FakeHV:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def state(self, dom: str) -> tuple[str, str]:
        return ("running", "")

    def ctrl_alt_del(self, dom: str) -> None:
        self.calls.append("ctrl_alt_del")

    def reset(self, dom: str) -> None:
        self.calls.append("reset")


def _grader(hv: FakeHV, incidents: list[str], diagnosis: str = "emergency") -> Grader:
    g = Grader.__new__(Grader)
    g.hv = hv
    g.lab = SimpleNamespace(target=lambda n: n, vm=lambda n: SimpleNamespace(domain=n))
    g.s = SimpleNamespace(incident=lambda node, kind, msg: incidents.append(msg))
    g.emit = lambda kind, data: None
    g._diagnose = lambda node: console.Diagnosis(diagnosis, diagnosis)
    return g


@pytest.fixture
def boot_ids(monkeypatch):
    """The node is unreachable (no boot id) until it has been rebooted one way or another."""
    state = {"rebooted": False}
    monkeypatch.setattr(remote, "boot_id", lambda t: "new-boot" if state["rebooted"] else None)
    monkeypatch.setattr(remote, "close_master", lambda t: None)
    monkeypatch.setattr(grader, "CTRL_ALT_DEL_GRACE", 0)
    state["commands"] = _commands(monkeypatch)
    return state


def _commands(monkeypatch, settle_rc: int = 0, settle_out: str = "running\n") -> list[tuple[str, bool]]:
    """Record what the grader runs on the node; `systemctl is-system-running --wait` answers as given."""
    ran: list[tuple[str, bool]] = []

    def run_cmd(t, command, *, timeout=60, as_root=True):
        ran.append((command, as_root))
        settle = "is-system-running" in command
        return proc.Result([command], settle_rc if settle else 0, settle_out if settle else "", "", 0.0)
    monkeypatch.setattr(remote, "run_cmd", run_cmd)
    return ran


def test_clean_reboot_with_ctrl_alt_del(monkeypatch, boot_ids):
    hv, incidents = FakeHV(), []

    def reachable(t, timeout):
        boot_ids["rebooted"] = True
        return True
    monkeypatch.setattr(remote, "wait_reachable", reachable)
    assert _grader(hv, incidents).verified_reboot(["node2"]) == {}
    assert hv.calls == ["ctrl_alt_del"]
    assert "Ctrl+Alt+Del" in incidents[0] and "reset" not in incidents[0]


def test_reset_when_ctrl_alt_del_does_not_help(monkeypatch, boot_ids):
    hv, incidents = FakeHV(), []
    monkeypatch.setattr(remote, "wait_reachable", lambda t, timeout: False)
    original_reset = hv.reset

    def reset(dom):
        original_reset(dom)
        boot_ids["rebooted"] = True
    hv.reset = reset
    assert _grader(hv, incidents).verified_reboot(["node2"]) == {}
    assert hv.calls == ["ctrl_alt_del", "reset"]


def test_no_reset_during_a_relabel(monkeypatch, boot_ids):
    hv, incidents = FakeHV(), []

    def not_yet(t, timeout):
        boot_ids["rebooted"] = True          # comes back later, after the relabel
        return False
    monkeypatch.setattr(remote, "wait_reachable", not_yet)
    assert _grader(hv, incidents, diagnosis="relabel").verified_reboot(["node2"]) == {}
    assert hv.calls == ["ctrl_alt_del"]


def _back(boot_ids: dict) -> bool:
    """Ctrl+Alt+Del worked: the unreachable node rebooted and answers."""
    boot_ids["rebooted"] = True
    return True


def _reachable_node(monkeypatch) -> list[str]:
    """A node that reboots when told to: its boot id changes with `systemctl reboot`."""
    ids = ["boot-1"]
    monkeypatch.setattr(remote, "boot_id", lambda t: ids[0])
    monkeypatch.setattr(remote, "close_master", lambda t: None)
    return ids


def test_checks_wait_until_the_boot_has_finished(monkeypatch):
    hv, incidents, events = FakeHV(), [], []
    ids = _reachable_node(monkeypatch)
    ran: list[tuple[str, bool]] = []

    def run_cmd(t, command, *, timeout=60, as_root=True):
        ran.append((command, as_root))
        if command == "systemctl reboot":
            ids[0] = "boot-2"
        return proc.Result([command], 0, "running\n" if "is-system-running" in command else "", "", 0.0)
    monkeypatch.setattr(remote, "run_cmd", run_cmd)
    g = _grader(hv, incidents)
    g.emit = lambda kind, data: events.append(data["stage"])
    assert g.verified_reboot(["node1"]) == {}
    # after the reboot, and without sudo: the grader's own sudo rule may be what was broken
    assert ran[0] == ("systemctl reboot", True)
    assert "systemctl is-system-running --wait" in ran[1][0] and ran[1][1] is False
    assert events == ["rebooting", "finishing", "back"]
    assert incidents == [] and hv.calls == []


@pytest.mark.parametrize(("rc", "out"), [(1, "degraded\n"), (0, "running\n")])
def test_a_finished_boot_is_no_incident_even_with_failed_units(monkeypatch, boot_ids, rc, out):
    hv, incidents = FakeHV(), []
    _commands(monkeypatch, rc, out)
    monkeypatch.setattr(remote, "wait_reachable", lambda t, timeout: _back(boot_ids))
    assert _grader(hv, incidents).verified_reboot(["node2"]) == {}
    assert not any("still starting" in i for i in incidents)


@pytest.mark.parametrize(("rc", "out"), [(124, ""), (1, "starting\n")])
def test_a_boot_that_does_not_finish_is_an_incident_and_grading_goes_on(monkeypatch, boot_ids, rc, out):
    hv, incidents = FakeHV(), []
    _commands(monkeypatch, rc, out)
    monkeypatch.setattr(remote, "wait_reachable", lambda t, timeout: _back(boot_ids))
    assert _grader(hv, incidents).verified_reboot(["node2"]) == {}
    assert any("still starting" in i for i in incidents)
