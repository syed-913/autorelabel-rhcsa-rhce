#!/usr/bin/env python3
"""The task bank's quality gate and report, without VMs.

Gate: every task has a passing self-test on libvirt and on VirtualBox for its current files
(the record's digest matches), and every draw of every task with random details passed the
sweep on its current files. An edited task fails CI until it is self-tested again.

Release gate (--release): no record may predate a change to what every task shares, which
the task's own digest can't see: the check and setup libraries, the lab's provisioning, the
box build. Between releases such records are only listed, so one shared change doesn't turn
CI red for hours of VM time; a release needs the full self-test on both hypervisors again.

Report: the same facts as a table in docs/guide/14-quality.md, between the quality markers.

    PYTHONPATH=src python scripts/dev/bank-quality.py --check             # CI: gate + report up to date
    PYTHONPATH=src python scripts/dev/bank-quality.py --check --release   # the release workflow
    PYTHONPATH=src python scripts/dev/bank-quality.py --write             # after a self-test run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from autorelabel import selftest  # noqa: E402
from autorelabel.bank import Bank, coverage, load_bank  # noqa: E402
from autorelabel.bank.select import sweep_draws  # noqa: E402

EXAMS = {"rhcsa": "RHCSA (EX200)", "rhce": "RHCE (EX294)"}
PROVIDERS = ("libvirt", "virtualbox")
PAGE = ROOT / "docs" / "guide" / "14-quality.md"
START, END = "<!-- quality:start -->", "<!-- quality:end -->"


def gate(bank: Bank, results: dict[str, dict], sweep: dict) -> list[str]:
    """What keeps the bank from shipping. results: provider -> self-test records; sweep: libvirt draws."""
    problems = []
    for tid, task in sorted(bank.tasks.items()):
        digest = selftest.task_digest(task)
        for provider in PROVIDERS:
            r = results[provider].get(tid)
            if not r:
                problems.append(f"{tid}: never self-tested on {provider}")
            elif r.get("digest") != digest:
                problems.append(f"{tid}: files changed since the {provider} self-test ({r.get('date', '?')})")
            elif r.get("status") != "pass":
                problems.append(f"{tid}: {provider} self-test {r.get('status')}: {r.get('detail', '')}".rstrip(": "))
        for i in range(sweep_draws(task) if sweep_draws(task) > 1 else 0):
            d = sweep.get(tid, {}).get(str(i))
            if not d or d.get("digest") != digest or d.get("status") != "pass":
                state = "missing" if not d else "stale" if d.get("digest") != digest else d.get("status")
                problems.append(f"{tid}: sweep draw {i + 1} of {sweep_draws(task)} {state}")
    return problems


def stale(bank: Bank, results: dict[str, dict]) -> list[str]:
    """Passing records made before something every task shares changed (or before that was recorded)."""
    now = selftest.shared_digests(bank.exam)
    notes = []
    for tid in sorted(bank.tasks):
        for provider in PROVIDERS:
            r = results[provider].get(tid)
            if not r or r.get("status") != "pass":
                continue        # the gate reports these
            if "shared" not in r:
                notes.append(f"{tid}: the {provider} self-test ({r.get('date', '?')}) has no record of the lab "
                             "and grader it ran with")
            elif changed := selftest.outdated(r, now):
                notes.append(f"{tid}: the {provider} self-test ({r.get('date', '?')}) predates a change to "
                             + " and ".join(selftest.SHARED[c] for c in changed))
    return notes


def facts(bank: Bank, results: dict[str, dict], sweep: dict) -> dict[str, str]:
    """One table column: what was tested, in words."""
    tasks = bank.tasks.values()
    tests = [p.name for t in tasks for p in (t.path / "tests").glob("*") if p.is_file()]
    cov = coverage.compute(bank)
    per_line = [len(c.tasks) for c in cov]
    practice = sum(1 for t in tasks if t.practice_only)
    random = [t for t in tasks if sweep_draws(t) > 1]
    draws = sum(sweep_draws(t) for t in random)
    row = {
        "Tasks": f"{len(bank.tasks)}" + (f" ({practice} practice-only)" if practice else ""),
        "Objective lines": f"{len(cov)}, each practised by {min(per_line)} or more tasks",
        "Accepted alternatives tested": str(sum(n.startswith("alt") for n in tests)),
        "Classic mistakes tested": str(sum(n.startswith("mistake") for n in tests)),
    }
    for provider, name in (("libvirt", "libvirt/KVM"), ("virtualbox", "VirtualBox")):
        recs = [results[provider][t.id] for t in tasks if t.id in results[provider]]
        current = sum(1 for t in tasks if t.id in selftest.verified(bank, provider))
        dates = sorted(r["date"] for r in recs if r.get("date"))
        boxes = sorted({" ".join(r["box"].split()[:2]) for r in recs if r.get("box")})
        when = f"on {dates[0]}" if dates and dates[0] == dates[-1] else f"{dates[0]} to {dates[-1]}" if dates else ""
        row[f"Self-tested on {name}"] = (f"{current} of {len(bank.tasks)} on their current files, "
                                        f"{', '.join(boxes)}, {when}" if dates else "none")
    now = selftest.shared_digests(bank.exam)
    fresh = {name: sum(1 for t in tasks if (r := results[provider].get(t.id)) and "shared" in r
                       and t.id in selftest.verified(bank, provider) and not selftest.outdated(r, now))
             for provider, name in (("libvirt", "libvirt/KVM"), ("virtualbox", "VirtualBox"))}
    row["Of those, with the current lab, box build and check libraries"] = ", ".join(
        f"{n} of {len(bank.tasks)} on {name}" for name, n in fresh.items())
    passed = sum(1 for t in random for i in range(sweep_draws(t))
                 if sweep.get(t.id, {}).get(str(i), {}).get("status") == "pass")
    row["Tasks with random details"] = f"{len(random)}: {passed} of {draws} draws passed"
    return row


def table(banks: list[Bank]) -> str:
    cols = {b.exam: facts(b, {p: selftest.load_results(b.exam, p) for p in PROVIDERS}, selftest.load_sweep(b.exam))
            for b in banks}
    lines = ["| | " + " | ".join(EXAMS[b.exam] for b in banks) + " |", "|---|" + "---|" * len(banks)]
    for key in cols[banks[0].exam]:
        lines.append(f"| **{key}** | " + " | ".join(cols[b.exam][key] for b in banks) + " |")
    return "\n".join(lines)


def update(page: str, body: str) -> str:
    block = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not block.search(page):
        raise SystemExit(f"{PAGE.name}: the {START} ... {END} markers are missing")
    return block.sub(lambda _: f"{START}\n{body}\n{END}", page)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help=f"update the table in {PAGE.name}")
    ap.add_argument("--check", action="store_true", help="fail if the gate fails or the table is stale")
    ap.add_argument("--release", action="store_true",
                    help="also fail on self-tests older than the lab, the box build or the check libraries")
    args = ap.parse_args()
    banks = [load_bank(exam) for exam in EXAMS]
    rc = 0
    for b in banks:
        results = {p: selftest.load_results(b.exam, p) for p in PROVIDERS}
        problems = gate(b, results, selftest.load_sweep(b.exam))
        for p in problems:
            print(f"QUALITY {b.exam}: {p}")
        print(f"{b.exam}: {len(b.tasks)} tasks, quality gate {'FAIL' if problems else 'ok'}")
        rc |= bool(problems)
        notes = stale(b, results)
        for n in notes if args.release else notes[:3]:
            print(f"{'RELEASE' if args.release else 'note'} {b.exam}: {n}")
        if notes:
            more = "" if args.release or len(notes) <= 3 else f" (3 shown; --release lists all {len(notes)})"
            print(f"{b.exam}: {len(notes)} self-test record(s) older than the lab or grader they would run with today, "
                  f"{'which blocks a release' if args.release else 'to be run again before the next release'}{more}")
        rc |= bool(notes and args.release)
    page = PAGE.read_text(encoding="utf-8")
    want = update(page, table(banks))
    if args.write:
        PAGE.write_text(want, encoding="utf-8")
        print(f"wrote the quality table in {PAGE.name}")
    elif args.check and want != page:
        print(f"{PAGE.name} is stale: run PYTHONPATH=src python scripts/dev/bank-quality.py --write")
        rc = 1
    elif not args.check:
        print(table(banks))
    return rc


if __name__ == "__main__":
    sys.exit(main())
