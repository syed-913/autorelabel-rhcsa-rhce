"""The dashboard's pages: plain data in, complete HTML out. No script, anywhere.

Every value goes through `e()` (html.escape): task titles and check details hold text that came
from a lab VM, which the candidate (or a task) controls. The server's Content-Security-Policy
forbids scripts as well, so even a missed escape could not run code.
"""

from __future__ import annotations

import html
import time
from typing import Any
from urllib.parse import urlencode

from .. import stats

EXAMS = {"rhcsa": "RHCSA", "rhce": "RHCE"}
PASS_MARK, TOTAL = 210, 300


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _pct(share: float | None) -> str:
    return "not yet" if share is None else f"{share * 100:.0f}%"


def _day(epoch: float | None) -> str:
    return "" if not epoch else time.strftime("%Y-%m-%d", time.localtime(epoch))


def _trend(delta: float | None) -> str:
    if delta is None:
        return ""
    if abs(delta) < 0.05:
        return "steady"
    return f"{'up' if delta > 0 else 'down'} {abs(delta) * 100:.0f} points"


def _link(path: str, exam: str, exams_only: bool, text: str, current: bool = False) -> str:
    query = urlencode({"exam": exam, **({"only": "exams"} if exams_only else {})})
    mark = ' aria-current="page"' if current else ""
    return f'<a href="{e(path)}?{e(query)}"{mark}>{e(text)}</a>'


def page(title: str, path: str, exam: str, exams_only: bool, body: str, unreadable: int = 0) -> str:
    nav = " ".join(_link(p, exam, exams_only, name, current=(p == path))
                   for p, name in (("/", "Overview"), ("/objectives", "Objectives"), ("/tasks", "Tasks and checks")))
    exams = " ".join(_link(path, key, exams_only, name, current=(key == exam)) for key, name in EXAMS.items())
    scope = " ".join([_link(path, exam, False, "exams and practice", current=not exams_only),
                      _link(path, exam, True, "exams only", current=exams_only)])
    note = (f'<p class="note">{unreadable} line(s) of the history could not be read and are left out.</p>'
            if unreadable else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · autorelabel results</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header>
<p class="brand">autorelabel results</p>
<nav aria-label="Views">{nav}</nav>
<nav aria-label="Exam">{exams}</nav>
<nav aria-label="Attempts counted">{scope}</nav>
</header>
<main>
<h1>{e(title)}</h1>
{note}
{body}
</main>
<footer>
<p>Read from this computer's own files. Nothing here is sent anywhere. Reload the page to update it.</p>
</footer>
</body>
</html>
"""


def score_chart(attempts: list[stats.Attempt]) -> str:
    """Scores over time against the pass mark, as inline SVG. Passes are circles, fails squares,
    and each point links to its attempt."""
    if not attempts:
        return ""
    width, height, left, bottom, top = 720, 240, 44, 26, 12
    span = max(len(attempts) - 1, 1)

    def x(i: int) -> float:
        return left + (width - left - 16) * (i / span if len(attempts) > 1 else 0.5)

    def y(score: float) -> float:
        return top + (height - top - bottom) * (1 - min(max(score, 0), TOTAL) / TOTAL)

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Scores of {len(attempts)} attempts, '
             f'pass mark {PASS_MARK} of {TOTAL}">']
    for mark in (0, 100, 200, 300):
        parts.append(f'<line class="grid" x1="{left}" x2="{width - 8}" y1="{y(mark):.1f}" y2="{y(mark):.1f}"/>'
                     f'<text class="axis" x="{left - 6}" y="{y(mark) + 4:.1f}" text-anchor="end">{mark}</text>')
    mark_y = y(PASS_MARK)
    parts.append(f'<line class="passmark" x1="{left}" x2="{width - 8}" y1="{mark_y:.1f}" y2="{mark_y:.1f}"/>'
                 f'<text class="axis" x="{width - 10}" y="{mark_y - 5:.1f}" text-anchor="end">'
                 f'pass mark {PASS_MARK}</text>')
    if len(attempts) > 1:
        points = " ".join(f"{x(i):.1f},{y(a.score):.1f}" for i, a in enumerate(attempts))
        parts.append(f'<polyline class="line" points="{points}"/>')
    for i, a in enumerate(attempts):
        label = f"{_day(a.graded_at)}: {a.score:.0f} of {TOTAL}, {'pass' if a.passed else 'fail'} ({a.mode})"
        shape = (f'<circle class="pass" cx="{x(i):.1f}" cy="{y(a.score):.1f}" r="5"/>' if a.passed else
                 f'<rect class="fail" x="{x(i) - 5:.1f}" y="{y(a.score) - 5:.1f}" width="10" height="10"/>')
        parts.append(f'<a href="/attempt/{e(a.session)}"><title>{e(label)}</title>{shape}</a>')
    parts.append("</svg>")
    return "".join(parts)


def _table(head: list[str], rows: list[list[str]], caption: str = "") -> str:
    """rows hold ready HTML: every cell was escaped where it was built."""
    cap = f"<caption>{e(caption)}</caption>" if caption else ""
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return (f"<table>{cap}<thead><tr>" + "".join(f"<th>{e(h)}</th>" for h in head)
            + f"</tr></thead><tbody>{body}</tbody></table>")


def overview(history: stats.History, exam: str, exams_only: bool, objectives: dict[str, tuple[str, str]],
             titles: dict[str, tuple[str, str]]) -> str:
    attempts = stats.select(history.attempts, exam, exams_only)
    if not attempts:
        body = (f"<p>No graded {e(EXAMS[exam])} attempt yet. Results appear here after an exam or a practice set "
                "has been graded.</p>")
        return page("Overview", "/", exam, exams_only, body, history.unreadable)
    o = stats.overview(attempts)
    facts = [("Attempts", str(o["attempts"])), ("Passed", str(o["passes"])),
             ("Best score", f"{o['best']:.0f} of {TOTAL}"),
             ("Latest scores", ", ".join(f"{s:.0f}" for s in o["last"]))]
    if o["median_minutes"] is not None:
        facts.append(("Median time used in exams", f"{o['median_minutes']:.0f} minutes"))
    lost = stats.not_persistent_total(attempts)
    if lost:
        facts.append(("Answers that did not survive the reboot", str(lost)))
    body = [score_chart(attempts),
            "<dl>" + "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in facts) + "</dl>"]
    weak = stats.weakest(stats.objective_rows(attempts, objectives))
    if weak:
        body.append("<h2>Objectives that keep costing points</h2>" + _table(
            ["Objective", "Tested", "Points, last results", "Trend"],
            [[e(r.title), str(r.tested), _pct(r.share), e(_trend(r.trend))] for r in weak]))
    repeated = stats.repeated_failures(stats.task_rows(attempts, titles))
    if repeated:
        body.append("<h2>Checks that failed more than once</h2>" + _table(
            ["Task", "Check", "Failed"],
            [[e(r.title), e(c["desc"]), f"{c['failed']} of {c['seen']}"] for r, c in repeated]))
    body.append("<h2>Attempts</h2>" + _table(
        ["Date", "Kind", "Score", "Result"],
        [[f'<a href="/attempt/{e(a.session)}">{e(_day(a.graded_at))}</a>', e(a.mode), f"{a.score:.0f}",
          "pass" if a.passed else "fail"] for a in reversed(attempts)]))
    return page("Overview", "/", exam, exams_only, "\n".join(body), history.unreadable)


def objectives_page(history: stats.History, exam: str, exams_only: bool,
                    objectives: dict[str, tuple[str, str]]) -> str:
    rows = stats.objective_rows(stats.select(history.attempts, exam, exams_only), objectives)
    body = ["<p>Each number is the share of points on the tasks that tested the objective, over the "
            f"latest {stats.RECENT} times it came up. Weakest first within each domain; objectives never "
            "tested yet are listed last.</p>"]
    domains: dict[str, list[stats.Row]] = {}
    for r in rows:
        domains.setdefault(r.group, []).append(r)
    for domain, group in domains.items():
        group.sort(key=lambda r: (r.share is None, r.tested < 2, r.share if r.share is not None else 0))
        body.append(f"<h2>{e(domain)}</h2>" + _table(
            ["Objective", "Tested", "Points, last results", "Trend", "Last tested"],
            [[e(r.title), str(r.tested), _pct(r.share), e(_trend(r.trend)), e(_day(r.last))] for r in group]))
    return page("Objectives", "/objectives", exam, exams_only, "\n".join(body), history.unreadable)


def tasks_page(history: stats.History, exam: str, exams_only: bool, titles: dict[str, tuple[str, str]]) -> str:
    attempts = stats.select(history.attempts, exam, exams_only)
    rows = stats.task_rows(attempts, titles)
    if not rows:
        body = "<p>No task has been graded yet, or the attempts are from before tasks were recorded.</p>"
        return page("Tasks and checks", "/tasks", exam, exams_only, body, history.unreadable)
    lost = stats.not_persistent_total(attempts)
    body = [f"<p>{len(rows)} different tasks so far, weakest first. A check marked "
            "<em>not persistent</em> passed before the grading reboot and failed after it."
            + (f" That happened {lost} time(s) in all." if lost else "") + "</p>"]
    for r in rows:
        head = (f"<h2>{e(r.title)}</h2><p>{e(r.group)}. Drawn {r.tested} time(s), {_pct(r.share)} of its points "
                f"over the latest results, last time {_pct(r.last_share)} on {e(_day(r.last))}.</p>")
        checks = [c for c in r.checks if c["failed"]]
        if checks:
            head += _table(["Check", "Node", "Failed", "Not persistent"],
                           [[e(c["desc"]) + (" (must not break)" if c["guard"] else ""), e(c["node"]),
                             f"{c['failed']} of {c['seen']}", str(c["not_persistent"] or "")] for c in checks])
        body.append(head)
    return page("Tasks and checks", "/tasks", exam, exams_only, "\n".join(body), history.unreadable)


def attempt_page(results: dict[str, Any], domain_titles: dict[str, str]) -> str:
    r = results
    exam = r.get("exam") if r.get("exam") in EXAMS else "rhcsa"
    used = f"{int(r.get('elapsed_s', 0)) // 60} of {int(r.get('duration_s', 0)) // 60} minutes"
    body = [f"<p><strong>{float(r.get('scaled_score', 0)):.0f} of {e(r.get('total_points', TOTAL))}</strong>, "
            f"{'pass' if r.get('passed') else 'fail'} (pass mark {e(r.get('pass_mark', PASS_MARK))}). "
            f"{e(str(r.get('mode', '')).capitalize())}, scoring {e(r.get('scoring', ''))}, time used {e(used)}, "
            f"graded {e(_day(r.get('graded_at')))}.</p>",
            "<p>The same report in the terminal: "
            f"<code>./autorelabel exam results {e(r.get('session', ''))}</code>. "
            "Retake on the results screen starts the same tasks over.</p>"]
    for key, name, names in (("by_difficulty", "Difficulty", {}), ("by_domain", "Domain", domain_titles)):
        table = r.get(key) if isinstance(r.get(key), dict) else {}
        body.append(_table([name, "Points"],
                           [[e(names.get(k, k)), f"{float(v.get('points', 0)):g} of {e(v.get('possible', 0))}"]
                            for k, v in table.items() if isinstance(v, dict)]))
    incidents = [i for i in r.get("incidents") or [] if isinstance(i, dict)]
    if incidents:
        body.append("<h2>Incidents</h2><ul>" + "".join(
            f"<li><strong>{e(i.get('node', ''))}</strong>: {e(i.get('message', ''))}</li>"
            for i in incidents) + "</ul>")
    body.append("<h2>Tasks</h2>")
    for t in r.get("tasks") or []:
        if not isinstance(t, dict):
            continue
        lost = set(t.get("not_persistent") or [])
        rows = []
        for c in t.get("post") or []:
            if not isinstance(c, dict) or c.get("status") == "n/a":
                continue
            status = str(c.get("status", ""))
            notes = []
            if c.get("guard"):
                notes.append("must not break")
            if c.get("id") in lost:
                notes.append("not persistent: it worked before the reboot")
            if status != "pass" and c.get("detail"):
                notes.append(str(c["detail"]))
            rows.append([f'<span class="{"ok" if status == "pass" else "bad"}">{e(status)}</span>',
                         e(c.get("desc", "")), e(c.get("node", "")), e("; ".join(notes))])
        body.append(f"<h3>Task {e(t.get('number', ''))}: {e(t.get('title', ''))}</h3>"
                    f"<p>{float(t.get('points', 0)):g} of {e(t.get('points_possible', 0))} points, "
                    f"{e(t.get('difficulty', ''))}.</p>" + _table(["Result", "Check", "Node", "Notes"], rows))
    return page(f"Attempt {r.get('session', '')}", "/", exam, False, "\n".join(body))


STYLE = """
:root { color-scheme: light dark; --fg: #1b1b1b; --bg: #fbfbf9; --muted: #5f6368; --line: #d5d5d0;
        --accent: #a30000; --ok: #1b6e2d; --bad: #a30000; }
@media (prefers-color-scheme: dark) {
  :root { --fg: #e6e6e3; --bg: #151515; --muted: #a2a6ab; --line: #3a3a3a; --accent: #ff7b72; --ok: #7ee787;
          --bad: #ff7b72; }
}
* { box-sizing: border-box; }
body { margin: 0 auto; padding: 1rem; max-width: 60rem; background: var(--bg); color: var(--fg);
       font: 15px/1.5 ui-monospace, "DejaVu Sans Mono", Menlo, Consolas, monospace; }
header { border-bottom: 1px solid var(--line); padding-bottom: .5rem; }
.brand { font-weight: bold; margin: 0 0 .3rem; }
nav { margin: .15rem 0; }
nav a { margin-right: 1rem; }
a { color: inherit; }
a[aria-current] { font-weight: bold; text-decoration: none; border-bottom: 2px solid var(--accent); }
h1 { font-size: 1.3rem; margin: 1rem 0 .5rem; }
h2 { font-size: 1.05rem; margin: 1.5rem 0 .4rem; }
h3 { font-size: 1rem; margin: 1.2rem 0 .2rem; }
table { border-collapse: collapse; width: 100%; margin: .4rem 0 1rem; }
th, td { text-align: left; vertical-align: top; padding: .25rem .6rem .25rem 0; border-bottom: 1px solid var(--line);
         overflow-wrap: anywhere; }
th { color: var(--muted); font-weight: normal; }
dl { display: grid; grid-template-columns: max-content 1fr; gap: .15rem 1rem; }
dt { color: var(--muted); }
dd { margin: 0; }
.note, footer { color: var(--muted); }
footer { border-top: 1px solid var(--line); margin-top: 2rem; }
.ok { color: var(--ok); }
.bad { color: var(--bad); font-weight: bold; }
svg { width: 100%; height: auto; margin: .5rem 0; }
.grid { stroke: var(--line); stroke-width: 1; }
.passmark { stroke: var(--accent); stroke-width: 1; stroke-dasharray: 6 4; }
.axis { fill: var(--muted); font-size: 11px; }
.line { fill: none; stroke: var(--fg); stroke-width: 1.5; }
.pass { fill: var(--ok); }
.fail { fill: var(--bad); }
code { background: color-mix(in srgb, var(--fg) 8%, transparent); padding: 0 .25rem; }
"""
