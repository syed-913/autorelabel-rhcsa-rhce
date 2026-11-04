"""The objective check (scripts/dev/objective-drift.py) reads both page layouts Red Hat uses."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("objective_drift", ROOT / "scripts" / "dev" / "objective-drift.py")
drift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drift)

NESTED = """<h2>Overview</h2><ul><li>Not an objective</li></ul>
<h2>Study points for the exam</h2><p>Candidates should be able to:</p>
<ul><li aria-level="1">Understand and use essential tools<ul>
<li aria-level="2">Use input-output redirection (&gt;, &gt;&gt;, |, 2&gt;, etc.)</li>
<li aria-level="2">Access remote systems using SSH</li></ul></li>
<li aria-level="1">Manage security<ul>
<li aria-level="2">Configure firewall settings using firewall&#8209;cmd</li></ul></li></ul>
<ul><li>Footer list</li></ul>"""

# The RHCE page: the heading is a paragraph, and one domain's lines are siblings, not nested.
FLAT = """<h2>In preparation</h2><p dir="ltr">Study points for the exam</p><ul>
<li aria-level="1">Configure Ansible managed nodes</li>
<li aria-level="2">Create and distribute SSH keys to managed nodes</li>
<li aria-level="2">Deploy files to managed nodes</li>
<li aria-level="1">Run playbooks<ul>
<li aria-level="2">Know how to run playbooks with ansible-navigator</li></ul></li></ul>"""


def test_a_nested_list_after_a_heading():
    assert drift.from_page(NESTED) == [
        "## Understand and use essential tools",
        "   Use input-output redirection (>, >>, |, 2>, etc.)",
        "   Access remote systems using SSH",
        "## Manage security",
        "   Configure firewall settings using firewall‑cmd",
    ]


def test_sibling_lines_after_a_paragraph_heading():
    assert drift.from_page(FLAT) == [
        "## Configure Ansible managed nodes",
        "   Create and distribute SSH keys to managed nodes",
        "   Deploy files to managed nodes",
        "## Run playbooks",
        "   Know how to run playbooks with ansible-navigator",
    ]


def test_a_page_without_study_points_is_an_error_not_a_change():
    try:
        drift.from_page("<h2>Exam format</h2><ul><li>Something</li></ul>")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_the_committed_objectives_read_as_an_outline():
    for exam in drift.EXAMS:
        url, lines = drift.from_bank(exam)
        assert url.startswith("https://www.redhat.com/")
        assert lines[0].startswith("## ") and all(ln.startswith(("## ", "   ")) for ln in lines)
