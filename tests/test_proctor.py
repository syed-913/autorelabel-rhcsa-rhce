"""The proctor's warning that the grader lost its way into a node."""

from __future__ import annotations

from autorelabel import proctor


def _health(**access):
    return {"nodes": {node: {"state": "running", "reason": "", "grader_access": ok} for node, ok in access.items()}}


def test_a_node_that_is_rebooting_is_not_reported():
    failing, warned = {}, set()
    assert proctor.lost_access(_health(node1=True, node2=False), failing, warned) == []     # mid-reboot
    assert failing == {"node2": 1}
    assert proctor.lost_access(_health(node1=True, node2=True), failing, warned) == []      # back
    assert failing == {} and warned == set()


def test_two_failed_checks_in_a_row_are_reported_once():
    failing, warned = {}, set()
    proctor.lost_access(_health(node1=True, node2=False), failing, warned)
    assert proctor.lost_access(_health(node1=True, node2=False), failing, warned) == ["node2"]
    assert proctor.lost_access(_health(node1=True, node2=False), failing, warned) == []     # already warned
    proctor.lost_access(_health(node1=True, node2=True), failing, warned)                    # repaired
    proctor.lost_access(_health(node1=True, node2=False), failing, warned)
    assert proctor.lost_access(_health(node1=True, node2=False), failing, warned) == ["node2"]


def test_a_powered_off_or_paused_node_is_neither_lost_nor_fine():
    failing, warned = {"node2": 1}, {"node1"}
    assert proctor.lost_access(_health(node1=None, node2=None), failing, warned) == []
    assert failing == {} and warned == {"node1"}
