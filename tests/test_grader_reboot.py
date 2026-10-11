"""The grading reboot of a node the grader cannot reach: Ctrl+Alt+Del first, a hard reset only
if that does not bring it back (and never in the middle of an SELinux relabel)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from autorelabel import console, grader, remote
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
    return state


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
