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


def test_a_record_made_before_a_shared_input_changed_is_named(tmp_path, monkeypatch):
    bank = load_bank("rhce")
    results, _ = _records("rhce")
    now = selftest.shared_digests("rhce")
    for recs in results.values():
        for r in recs.values():
            r["shared"] = dict(now)
    assert quality.stale(bank, results) == []

    tid = sorted(bank.tasks)[0]
    results["virtualbox"][tid]["shared"]["lab"] = "000000000000"
    assert quality.stale(bank, results) == [
        f"{tid}: the virtualbox self-test ({results['virtualbox'][tid]['date']}) predates a change to "
        "the lab's provisioning"]

    del results["libvirt"][tid]["shared"]           # a record from before the digests existed
    assert any(n.startswith(f"{tid}: the libvirt self-test") and "no record" in n for n in quality.stale(bank, results))


def test_shared_digests_follow_the_files_of_their_own_exam(tmp_path, monkeypatch):
    rhcsa, rhce = selftest.shared_inputs("rhcsa"), selftest.shared_inputs("rhce")
    names = lambda inputs: {p.name for p in inputs if isinstance(p, Path)}          # noqa: E731
    assert {"check-lib.sh", "setup-lib.sh", "pools.yaml"} <= names(rhcsa["checks"])
    assert "control.sh" in names(rhce["lab"]) and "control.sh" not in names(rhcsa["lab"])
    assert "node.sh" in names(rhcsa["lab"]) and "ks.cfg.pkrtpl" in names(rhcsa["box"])
    # how the grader wraps a check is part of what a check is
    before = selftest.shared_digests("rhcsa")
    monkeypatch.setattr(selftest.grader, "check_script", lambda lib, check: f"{lib}\n{check}\n")
    after = selftest.shared_digests("rhcsa")
    assert after["checks"] != before["checks"] and after["lab"] == before["lab"] and after["box"] == before["box"]
