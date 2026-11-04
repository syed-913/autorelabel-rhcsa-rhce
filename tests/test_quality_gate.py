"""The quality gate (scripts/dev/bank-quality.py) fails an edited or untested task."""

import copy
import importlib.util
from pathlib import Path

from autorelabel import selftest
from autorelabel.bank import load_bank
from autorelabel.bank.select import sweep_draws

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bank_quality", ROOT / "scripts" / "dev" / "bank-quality.py")
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


def _records(exam):
    return {p: selftest.load_results(exam, p) for p in quality.PROVIDERS}, selftest.load_sweep(exam)


def test_the_committed_records_pass_the_gate():
    for exam in quality.EXAMS:
        bank = load_bank(exam)
        assert quality.gate(bank, *_records(exam)) == []


def test_an_edited_untested_or_failing_task_fails_the_gate():
    bank = load_bank("rhcsa")
    results, sweep = _records("rhcsa")
    tid = next(t.id for t in bank.tasks.values() if sweep_draws(t) > 1)

    edited = copy.deepcopy(results)
    edited["libvirt"][tid]["digest"] = "000000000000"
    problems = quality.gate(bank, edited, sweep)
    assert any(p.startswith(f"{tid}: files changed since the libvirt self-test") for p in problems)

    untested = copy.deepcopy(results)
    del untested["virtualbox"][tid]
    assert f"{tid}: never self-tested on virtualbox" in quality.gate(bank, untested, sweep)

    failed = copy.deepcopy(sweep)
    failed[tid]["0"]["status"] = "fail"
    assert any("sweep draw 1 of" in p and p.endswith("fail") for p in quality.gate(bank, results, failed))


def test_the_report_names_both_exams_and_both_hypervisors():
    table = quality.table([load_bank(exam) for exam in quality.EXAMS])
    assert "RHCSA (EX200)" in table and "RHCE (EX294)" in table
    assert "Self-tested on libvirt/KVM" in table and "Self-tested on VirtualBox" in table
