#!/usr/bin/env python3
"""Has Red Hat changed the RHCSA or RHCE objectives? Compares each exam page's "Study points
for the exam" with banks/<exam>/objectives.yaml, line by line, after normalising whitespace,
entities and typographic quotes.

Exit status: 0 unchanged, 1 changed (the diff is printed, and written to --markdown as an
issue body), 2 a page couldn't be fetched or read (a page redesign, not an objective change).

    PYTHONPATH=src python scripts/dev/objective-drift.py [--markdown drift.md] [--page exam=file.html]
"""

from __future__ import annotations

import argparse
import difflib
import html
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EXAMS = {"rhcsa": "EX200", "rhce": "EX294"}
HEADING = "Study points for the exam"


def norm(text: str) -> str:
    text = html.unescape(text).replace(" ", " ")
    text = text.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                                         "–": "-", "—": "-"}))
    return re.sub(r"\s+", " ", text).strip()


class StudyPoints(HTMLParser):
    """Collects the first list after the text "Study points for the exam" (a heading on the
    RHCSA page, a paragraph on the RHCE one): depth-1 items are domains, depth-2 items their
    objective lines, deeper items sub-points of the line above. An item's aria-level wins over
    its nesting: the RHCE page lists some objective lines as siblings of their domain."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.started = self.done = False
        self.depth = 0
        self.items: list[list] = []   # [level, text parts] of each <li>, in document order
        self.open: list[int] = []     # indexes of the open <li> elements

    def handle_starttag(self, tag, attrs):
        if self.done or not self.started:
            return
        if tag == "ul":
            self.depth += 1
        elif tag == "li":
            level = dict(attrs).get("aria-level") or ""
            self.items.append([int(level) if level.isdigit() else self.depth, []])
            self.open.append(len(self.items) - 1)

    def handle_endtag(self, tag):
        if self.done or not self.started:
            return
        if tag == "li" and self.open:
            self.open.pop()
        elif tag == "ul":
            self.depth -= 1
            self.done = self.depth == 0

    def handle_data(self, data):
        if not self.started:
            self.started = norm(data) == HEADING
        elif self.open:
            self.items[self.open[-1]][1].append(data)


def from_page(page: str) -> list[str]:
    """The study points as outline lines, "## domain" then an indented line per objective, in page order."""
    p = StudyPoints()
    p.feed(page)
    marks = {1: "## ", 2: "   "}
    out = [marks.get(level, "      ") + norm("".join(parts)) for level, parts in p.items if norm("".join(parts))]
    if not out:
        raise ValueError(f'no "{HEADING}" list found')
    return out


def from_bank(exam: str) -> tuple[str, list[str]]:
    data = yaml.safe_load((ROOT / "banks" / exam / "objectives.yaml").read_text(encoding="utf-8"))
    lines = []
    for d in data["domains"]:
        lines.append(f"## {norm(d['title'])}")
        # A domain whose page bullet is itself an objective repeats its title as a line: skip that mirror.
        lines += [f"   {norm(o['text'])}" for o in d["objectives"] if norm(o["text"]) != norm(d["title"])]
    return data["source_url"], lines


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "autorelabel objective check (+https://autorelabel.dpdns.org)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--markdown", type=Path, help="write the differences as an issue body")
    ap.add_argument("--page", action="append", default=[], metavar="EXAM=FILE", help="read a saved page")
    args = ap.parse_args()
    saved = dict(p.split("=", 1) for p in args.page)
    report, rc = [], 0
    for exam, code in EXAMS.items():
        url, committed = from_bank(exam)
        try:
            page = Path(saved[exam]).read_text(encoding="utf-8") if exam in saved else fetch(url)
            published = from_page(page)
        except (OSError, ValueError) as exc:
            print(f"{exam}: couldn't read {url}: {exc}")
            return 2
        diff = list(difflib.unified_diff(committed, published, f"banks/{exam}/objectives.yaml", url, lineterm="", n=1))
        n = sum(1 for ln in published if ln.startswith("   ") and not ln.startswith("      "))
        print(f"{exam}: {'CHANGED' if diff else 'unchanged'} ({n} objective lines on the page)")
        if diff:
            rc = 1
            print("\n".join(diff))
            report += [f"## {exam.upper()} ({code})", "", f"Page: {url}", "", "```diff", *diff, "```", ""]
    if rc and args.markdown:
        args.markdown.write_text("\n".join([
            "The monthly objective check found differences between Red Hat's exam pages and the objectives "
            "in this repository. Lines starting with `-` are in the repository, `+` on Red Hat's page.", "",
            *report,
            "To do: update `banks/<exam>/objectives.yaml` (text and `source_checked`), add or retag tasks so every "
            "line keeps 2 or more, self-test them, then run `bank coverage --write` and "
            "`scripts/dev/bank-quality.py --write`.", ""]), encoding="utf-8")
    return rc


if __name__ == "__main__":
    sys.exit(main())
