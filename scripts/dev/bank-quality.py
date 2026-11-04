#!/usr/bin/env python3
"""The task bank's quality gate and report, without VMs.

Gate: every task has a passing self-test on libvirt and on VirtualBox for its current files
(the record's digest matches), and every draw of every task with random details passed the
sweep on its current files. An edited task fails CI until it is self-tested again.

Report: the same facts as a table in docs/guide/14-quality.md, between the quality markers.

    PYTHONPATH=src python scripts/dev/bank-quality.py --check    # CI: gate + report up to date
    PYTHONPATH=src python scripts/dev/bank-quality.py --write    # after a self-test run
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
    args = ap.parse_args()
    banks = [load_bank(exam) for exam in EXAMS]
    rc = 0
    for b in banks:
        problems = gate(b, {p: selftest.load_results(b.exam, p) for p in PROVIDERS}, selftest.load_sweep(b.exam))
        for p in problems:
            print(f"QUALITY {b.exam}: {p}")
        print(f"{b.exam}: {len(b.tasks)} tasks, quality gate {'FAIL' if problems else 'ok'}")
        rc |= bool(problems)
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
