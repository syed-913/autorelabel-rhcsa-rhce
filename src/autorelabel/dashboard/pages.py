"""The dashboard's pages: plain data in, complete HTML out. No script, anywhere.

Every value goes through `e()` (html.escape): task titles and check details hold text that came
from a lab VM, which the candidate (or a task) controls. The server's Content-Security-Policy
forbids scripts and inline styles as well, so even a missed escape could not run code. That is
also why sizes that come from data (bars, the score chart) are SVG attributes and not styles,
and why the entrance delays are classes (`d1` to `d12`) and not inline values. The look is in
`style.css`; everything that moves there is CSS.
"""

from __future__ import annotations

import html
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from .. import stats

EXAMS = {"rhcsa": "RHCSA", "rhce": "RHCE"}
PASS_MARK, TOTAL = 210, 300
STYLE = (Path(__file__).with_name("style.css")).read_text(encoding="utf-8")


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _pct(share: float | None) -> str:
    return "not yet" if share is None else f"{share * 100:.0f}%"


def _day(epoch: float | None, year: bool = False) -> str:
    """'9 Nov', or '9 November 2026' with the year."""
    if not epoch:
        return ""
    try:
        t = time.localtime(epoch)
    except (OverflowError, ValueError, OSError):      # a hand-edited date the clock can't show
        return ""
    return f"{t.tm_mday} {time.strftime('%B %Y' if year else '%b', t)}"


def _clock(epoch: float | None) -> str:
    try:
        return "" if not epoch else time.strftime("%H:%M", time.localtime(epoch))
    except (OverflowError, ValueError, OSError, TypeError):
        return ""


def _duration(seconds: float | None) -> str:
    if not seconds:
        return ""
    minutes = round(seconds / 60)
    hours, rest = divmod(minutes, 60)
    return f"{hours} h {rest:02d} min" if hours else f"{rest} min"


def _trend(delta: float | None) -> str:
    if delta is None:
        return ""
    if delta >= 0.05:
        return "↑ improving"
    if delta <= -0.05:
        return "↓ falling"
    return "→ level"


def _delay(i: int) -> str:
    return f"d{min(i, 12) + 1}"


def _query(exam: str, exams_only: bool) -> str:
    return urlencode({"exam": exam, **({"only": "exams"} if exams_only else {})})


def _bar(share: float | None, width: int = 140) -> str:
    """A share as a small SVG bar: its width is an attribute, so no inline style is needed."""
    fill = max(0.0, min(share or 0.0, 1.0)) * (width - 2)
    inner = f'<rect class="fill" x="1" y="1" width="{fill:.1f}" height="8"/>' if share else ""
    return (f'<svg class="bar" viewBox="0 0 {width} 10" preserveAspectRatio="none" aria-hidden="true">'
            f'<rect class="track" x=".5" y=".5" width="{width - 1}" height="9"/>{inner}</svg>')


def _mark(share: float | None) -> str:
    """The word and the mark for a share of points, so colour is never the only signal."""
    if share is None:
        return ""
    if share >= 0.999:
        return '<span class="ok">✓</span>'
    if share <= 0.001:
        return '<span class="bad">✗</span>'
    return '<span class="warn">◐</span>'


def page(title: str, path: str, exam: str, exams_only: bool, body: str, unreadable: int = 0, *,
         heading: str = "", lede: str = "", filters: bool = True) -> str:
    query = _query(exam, exams_only)
    current = ' aria-current="page"'
    tabs = "".join(
        f'<a href="{p}?{e(query)}"{current if p == path else ""}>{name}</a>'
        for p, name in (("/", "Overview"), ("/objectives", "Objectives"), ("/tasks", "Tasks and checks")))

    def chip(text: str, key: str, only: bool, current: bool) -> str:
        mark = ' aria-current="true"' if current else ""
        return f'<a class="chip" href="{e(path)}?{e(_query(key, only))}"{mark}>{e(text)}</a>'

    controls = ""
    if filters:
        exams = "".join(chip(name, key, exams_only, key == exam) for key, name in EXAMS.items())
        scope = chip("Exams and practice", exam, False, not exams_only) + chip("Exams only", exam, True, exams_only)
        controls = (f'<div class="filters"><div class="filter"><span>Exam</span>{exams}</div>'
                    f'<div class="filter"><span>Count</span>{scope}</div></div>')
    note = ""
    if unreadable:
        what = "1 attempt" if unreadable == 1 else f"{unreadable} attempts"
        note = (f'<div class="notice rise" role="status"><b>NOTE</b><span>{what} could not be read and '
                f'{"is" if unreadable == 1 else "are"} left out of every number on these pages. Their lines '
                "in the history file are damaged. Nothing was changed or removed.</span></div>")
    intro = ""
    if heading:
        intro = (f'<div class="intro"><div class="rise"><h1>{e(heading)}</h1>'
                 f'{f"<p class=lede>{lede}</p>" if lede else ""}</div>{controls}</div>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{e(title)} · autorelabel results</title>
<link rel="preload" href="/fonts/fraunces-650.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/style.css">
</head>
<body>
<div class="heat"></div>
<div class="wrap">
<header class="top">
<div class="brand">autorelabel <span>results</span></div>
<nav class="pages" aria-label="Pages">{tabs}</nav>
<div class="readonly">Read only. Served from this computer.</div>
</header>
{note}
{intro}
<main>
{body}
</main>
<footer class="foot">These pages read your graded attempts and change nothing. Reload to see a new result.
Stop them with Ctrl+C in the terminal where you started them.</footer>
</div>
</body>
</html>
"""


# --- the overview --------------------------------------------------------------------------------

def score_chart(attempts: list[stats.Attempt]) -> str:
    """Scores over time against the pass mark. Passes are filled circles, fails open squares;
    every point links to its attempt and shows its details on hover or keyboard focus."""
    if not attempts:
        return ""
    width, left, right, top, base = 920, 84, 900, 40, 280
    n = len(attempts)
    step = (right - left - 48) / max(n - 1, 1)

    def x(i: int) -> float:
        return left + 24 + (i * step if n > 1 else (right - left - 48) / 2)

    def y(score: float) -> float:
        return base - (base - top) * min(max(score, 0.0), TOTAL) / TOTAL

    scores = ", ".join(f"{a.score:.0f}" for a in attempts)
    passed = sum(1 for a in attempts if a.passed)
    label = (f"Scores of {n} attempt{'s' if n != 1 else ''}: {scores} of {TOTAL}. The pass mark is {PASS_MARK}. "
             f"{passed} passed.")
    parts = [f'<svg viewBox="0 0 {width} 330" role="img" aria-label="{e(label)}">']
    # the pass mark is labelled in the axis gutter, where no point can sit on it; the 200 line
    # beside it goes without a label, as the two would overlap
    for mark in (300, 200, 100):
        label = ("" if mark == 200 else
                 f'<text class="axis" x="{left - 10}" y="{y(mark) + 4:.0f}" text-anchor="end">{mark}</text>')
        parts.append(f'<line class="grid" x1="{left}" y1="{y(mark):.0f}" x2="{right}" y2="{y(mark):.0f}"/>{label}')
    parts.append(f'<line class="base" x1="{left}" y1="{base}" x2="{right}" y2="{base}"/>'
                 f'<text class="axis" x="{left - 10}" y="{base + 4}" text-anchor="end">0</text>')
    pm = y(PASS_MARK)
    parts.append(f'<line class="passmark" x1="{left}" y1="{pm:.1f}" x2="{right}" y2="{pm:.1f}"/>'
                 f'<text class="passlabel" x="{left - 10}" y="{pm - 2:.1f}" text-anchor="end">pass</text>'
                 f'<text class="passlabel" x="{left - 10}" y="{pm + 11:.1f}" text-anchor="end">{PASS_MARK}</text>')
    if n > 1:
        points = " ".join(f"{x(i):.1f},{y(a.score):.1f}" for i, a in enumerate(attempts))
        parts.append(f'<polyline class="line" points="{points}"/>')
    labels_every = max(1, (n + 11) // 12)          # dates under at most about twelve points
    for i, a in enumerate(attempts):
        px, py = x(i), y(a.score)
        verdict = "passed" if a.passed else "failed"
        tip = f"{_day(a.graded_at)}, {a.mode}: {a.score:.0f} of {TOTAL}, {verdict}"
        shape = (f'<circle class="shape" cx="{px:.1f}" cy="{py:.1f}" r="7"/>' if a.passed else
                 f'<rect class="shape" x="{px - 6:.1f}" y="{py - 6:.1f}" width="12" height="12"/>')
        tx = min(max(px - 128, left), right - 256)
        ty = py - 70 if py > top + 74 else py + 18
        diff = a.score - PASS_MARK
        second = f"{abs(diff):.0f} {'above' if diff >= 0 else 'below'} the pass mark"
        under = ""
        if i % labels_every == 0 or i == n - 1:
            under = (f'<text class="date" x="{px:.1f}" y="302" text-anchor="middle">{e(_day(a.graded_at))}</text>'
                     f'<text class="kind" x="{px:.1f}" y="318" text-anchor="middle">{e(a.mode)}</text>')
        parts.append(
            f'<a class="pt {_delay(i)}" href="/attempt/{e(a.session)}"><title>{e(tip)}</title>'
            f'<line class="guide" x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{base}"/>'
            f'<rect class="hit" x="{px - 16:.1f}" y="{top - 10}" width="32" height="{base - top + 50}"/>'
            f'{shape}<text class="score" x="{px:.1f}" y="{py - 14:.1f}" text-anchor="middle">{a.score:.0f}</text>'
            f"{under}"
            f'<g class="tip"><rect x="{tx:.1f}" y="{ty:.1f}" width="256" height="52" rx="2"/>'
            f'<text class="strong" x="{tx + 12:.1f}" y="{ty + 21:.1f}">{a.score:.0f} / {TOTAL} · '
            f'{"✓ pass" if a.passed else "✗ fail"}</text>'
            f'<text x="{tx + 12:.1f}" y="{ty + 40:.1f}">{e(_day(a.graded_at))} · {e(second)}</text></g></a>')
    parts.append("</svg>")
    legend = ('<div class="legend"><span><svg viewBox="0 0 14 14" aria-hidden="true">'
              '<circle class="dot" cx="7" cy="7" r="6"/>'
              '</svg> filled circle: passed</span><span><svg viewBox="0 0 14 14" aria-hidden="true">'
              '<rect class="sq" x="2" y="2" width="10" height="10"/></svg> open square: failed</span>'
              "<span>Point at a result to see it; select it to open its report.</span></div>")
    return f'<div class="panel chart">{"".join(parts)}{legend}</div>'


def _tiles(items: list[tuple[str, str, str]]) -> str:
    return '<div class="tiles">' + "".join(
        f'<div class="tile rise {_delay(i)}"><div class="label">{e(label)}</div><div class="value">{e(value)}</div>'
        f'<div class="note">{e(note)}</div></div>' for i, (label, value, note) in enumerate(items)) + "</div>"


def _time_used(a: stats.Attempt) -> str:
    if a.mode != "exam":
        return "not timed"
    return _duration((a.results or {}).get("elapsed_s")) or "unknown"


def empty_page(exam: str, exams_only: bool, unreadable: int = 0) -> str:
    body = ('<div class="empty rise"><p>Your results appear here after your first graded '
            f"{e(EXAMS[exam])} attempt: scores over time, the objectives that cost you points, and every check "
            "the grader ran.</p><p>Start an exam or a practice session in a terminal:</p>"
            '<div class="cmd"><span>$ </span>./autorelabel</div>'
            "<p>Then load this page again. Objectives and Tasks stay empty until then as well.</p></div>")
    return page("Overview", "/", exam, exams_only, body, unreadable, heading="Nothing graded yet")


def overview(history: stats.History, exam: str, exams_only: bool, objectives: dict[str, tuple[str, str]],
             titles: dict[str, tuple[str, str]]) -> str:
    attempts = stats.select(history.attempts, exam, exams_only)
    if not attempts:
        return empty_page(exam, exams_only, history.unreadable)
    o = stats.overview(attempts)
    n_exam = sum(1 for a in attempts if a.mode == "exam")
    n_practice = len(attempts) - n_exam
    best = max(attempts, key=lambda a: a.score)
    last = attempts[-3:]
    above = sum(1 for a in last if a.score >= PASS_MARK)
    passes = [i for i, a in enumerate(attempts) if a.passed]
    passed_note = ("not yet" if not passes else
                   f"the last {len(passes)}" if passes == list(range(len(attempts) - len(passes), len(attempts)))
                   and len(passes) > 1 else f"of {len(attempts)}")
    tiles = [("Attempts", str(len(attempts)), f"{n_exam} exam{'s' * (n_exam != 1)}, {n_practice} practice"),
             ("Passed", str(o["passes"]), passed_note),
             ("Best score", f"{best.score:.0f}", f"of {TOTAL}, on {_day(best.graded_at)}"),
             ("Last three" if len(last) == 3 else "Latest", " ".join(f"{a.score:.0f}" for a in last),
              "each above 210" if above == len(last) else f"{above} of {len(last)} above {PASS_MARK}")]
    if o["median_minutes"] is not None:
        tiles.append(("Median time", _duration(o["median_minutes"] * 60), "used in your exams"))
    first, newest = attempts[0], attempts[-1]
    span = (f"{_day(first.graded_at)} to {_day(newest.graded_at, year=True)}" if len(attempts) > 1
            else _day(newest.graded_at, year=True))
    lede = f"{len(attempts)} graded attempt{'s' * (len(attempts) != 1)}, {e(span)}."
    body = [_tiles(tiles),
            '<section><h2>Scores over time</h2><p class="sub">Out of 300. You pass at 210. Every point is also '
            "a row in the table at the end of this page.</p>" + score_chart(attempts) + "</section>"]

    weak = stats.weakest(stats.objective_rows(attempts, objectives))
    left = ['<section><h2>What keeps costing you points</h2><p class="sub">The objectives with the lowest share '
            "of points, among those tested at least twice. Each number is the mean of the latest five "
            "results.</p>"]
    if weak:
        for i, r in enumerate(weak):
            trend = _trend(r.trend)
            left.append(f'<div class="item rise {_delay(i)}"><div class="head"><a href="/objectives?'
                        f'{e(_query(exam, exams_only))}#obj-{e(r.key)}">{e(r.title)}</a><span class="num">'
                        f"{_pct(r.share)}</span></div>{_bar(r.share, 400)}<div class=\"meta\">{e(r.group)} · tested "
                        f"{r.tested} times{f' · {trend}' if trend else ''}</div></div>")
    else:
        left.append('<p class="muted">Nothing yet: an objective appears here once it has been tested twice and '
                    "cost you points.</p>")
    left.append(f'<p><a href="/objectives?{e(_query(exam, exams_only))}">All {len(objectives)} objectives, tested '
                "or not</a></p></section>")

    task_rows = stats.task_rows(attempts, titles)
    repeated = stats.repeated_failures(task_rows)
    right = ['<section><h2>Checks you failed more than once</h2><p class="sub">One check is one thing the grader '
             "looked at. These failed in at least two attempts.</p>"]
    if repeated:
        for i, (r, c) in enumerate(repeated):
            reboot = (f'<div class="reboot">↻ lost in the reboot {c["not_persistent"]} '
                      f'time{"s" * (c["not_persistent"] != 1)}: it worked before the grading reboot</div>'
                      if c["not_persistent"] else "")
            right.append(f'<div class="item rise {_delay(i)}"><div class="head"><span><b>{e(c["desc"])}</b></span>'
                         f'<span class="num bad">✗ {c["failed"]} of {c["seen"]}</span></div><div class="meta">'
                         f'<a href="/tasks?{e(_query(exam, exams_only))}#task-{e(r.key)}">{e(r.title)}</a> · '
                         f'{e(c["node"])}</div>{reboot}</div>')
    else:
        right.append('<p class="muted">None so far. A check shows up here when it fails in two attempts.</p>')
    lost = stats.not_persistent_total(attempts)
    if lost:
        right.append(f'<div class="callout"><div class="label">↻ Lost in the reboot</div><div><span class="big">{lost}'
                     f"</span> answer{'s' * (lost != 1)} worked before the grading reboot and not after it, across "
                     f"your {len(attempts)} attempts. On the exam, work that does not survive a reboot scores "
                     "nothing.</div></div>")
    right.append("</section>")
    body.append(f'<div class="cols">{"".join(left)}{"".join(right)}</div>')

    rows = []
    for a in reversed(attempts):
        verdict = '<span class="pill ok">✓ Pass</span>' if a.passed else '<span class="pill bad">✗ Fail</span>'
        rows.append(f'<tr><td class="nowrap">{e(_day(a.graded_at, year=True))}</td><td>{e(a.mode.capitalize())}</td>'
                    f'<td class="r num">{a.score:.0f} / {TOTAL}</td><td>{verdict}</td>'
                    f'<td class="nowrap mono">{e(_time_used(a))}</td>'
                    f'<td><a class="open" href="/attempt/{e(a.session)}">Open</a></td></tr>')
    body.append('<section><h2>Every attempt</h2><div class="table-wrap"><table><thead><tr><th scope="col">Graded</th>'
                '<th scope="col">Kind</th><th scope="col" class="r">Score</th><th scope="col">Result</th>'
                '<th scope="col">Time used</th><th scope="col">Report</th></tr></thead><tbody>'
                + "".join(rows) + "</tbody></table></div></section>")
    body.append('<div class="later"><div class="label">Kept for later</div><div>Time per task. autorelabel does not '
                "record it yet. When it does, this is where you will see which tasks take you longest.</div></div>")
    return page("Overview", "/", exam, exams_only, "\n".join(body), history.unreadable,
                heading=f"Your {EXAMS[exam]} results", lede=lede)


# --- objectives ----------------------------------------------------------------------------------

def objectives_page(history: stats.History, exam: str, exams_only: bool,
                    objectives: dict[str, tuple[str, str]]) -> str:
    rows = stats.objective_rows(stats.select(history.attempts, exam, exams_only), objectives)
    tested = sum(1 for r in rows if r.tested)
    lede = (f"The official list, in its order. Your attempts have tested {tested} of the {len(rows)} objectives. "
            f"A number is your share of the points, as the mean of the latest {stats.RECENT} results.")
    domains: dict[str, list[stats.Row]] = {}
    for r in rows:
        domains.setdefault(r.group, []).append(r)
    body = []
    for d, (domain, group) in enumerate(domains.items()):
        seen = [r for r in group if r.share is not None]
        mean = sum(r.share or 0 for r in seen) / len(seen) if seen else None
        lines = [f'<section class="domain rise {_delay(d)}"><div class="domain-head"><h2>{e(domain)}</h2>'
                 f'<div class="sum">{len(seen)} of {len(group)} tested'
                 f'{f" · {_pct(mean)}" if mean is not None else ""}</div></div>']
        for r in group:
            if r.share is None:
                lines.append(f'<div class="obj untested" id="obj-{e(r.key)}"><div>{e(r.title)}</div>'
                             '<div class="small">not tested yet</div></div>')
                continue
            trend = _trend(r.trend) or "needs 3 results"
            lines.append(f'<div class="obj" id="obj-{e(r.key)}"><div>{e(r.title)}</div>{_bar(r.share)}'
                         f'<div class="share">{_pct(r.share)}</div><div class="small">{r.tested} '
                         f'time{"s" * (r.tested != 1)}</div><div class="small">{e(trend)}</div>'
                         f'<div class="small">{e(_day(r.last))}</div></div>')
        lines.append("</section>")
        body.append("".join(lines))
    body.append('<div class="keys"><span>Columns: share of points, times tested, trend, last tested.</span>'
                "<span>Trend compares your last two results with the three before them. It needs three "
                "results.</span></div>")
    return page("Objectives", "/objectives", exam, exams_only, "\n".join(body), history.unreadable,
                heading=f"{EXAMS[exam]} objectives", lede=lede)


# --- tasks and checks ----------------------------------------------------------------------------

def _latest_points(attempts: list[stats.Attempt], task_id: str) -> tuple[float, float] | None:
    for a in reversed(attempts):
        for t in (a.results or {}).get("tasks", []):
            if isinstance(t, dict) and t.get("task_id") == task_id:
                return float(t.get("points", 0) or 0), float(t.get("points_possible", 0) or 0)
    return None


def tasks_page(history: stats.History, exam: str, exams_only: bool, titles: dict[str, tuple[str, str]]) -> str:
    attempts = stats.select(history.attempts, exam, exams_only)
    rows = stats.task_rows(attempts, titles)
    heading = f"{EXAMS[exam]} tasks you have met"
    if not rows:
        body = ('<p class="muted">No task has been graded yet, or the attempts are from before autorelabel recorded '
                "their tasks.</p>")
        return page("Tasks and checks", "/tasks", exam, exams_only, body, history.unreadable, heading=heading)
    lede = (f"{len(rows)} of the {len(titles)} tasks in the bank, weakest first. Open a task to see which of its "
            "checks "
            "failed, how often, and whether your answer was lost in the reboot.")
    body = []
    for i, r in enumerate(rows):
        nodes = sorted({c["node"] for c in r.checks if c["node"]})
        latest = _latest_points(attempts, r.key)
        last = (f"{_mark(r.last_share)} last: {latest[0]:g} / {latest[1]:g}" if latest else
                f"{_mark(r.last_share)} last: {_pct(r.last_share)}")
        meta = " · ".join(x for x in (r.group, ", ".join(nodes),
                                      f"met {r.tested} time{'s' * (r.tested != 1)}, last on {_day(r.last)}") if x)
        checks = [c for c in r.checks]
        if checks:
            table_rows = "".join(
                f'<tr><td>{e(c["desc"])}{" <span class=muted>(must not break)</span>" if c["guard"] else ""}</td>'
                f'<td>{e(c["node"])}</td><td class="nowrap">'
                + (f'<span class="bad">✗ {c["failed"]} of {c["seen"]}</span>' if c["failed"] else
                   '<span class="ok">✓ never</span>')
                + '</td><td class="nowrap">'
                + (f'<span class="warn">↻ {c["not_persistent"]} time{"s" * (c["not_persistent"] != 1)}</span>'
                   if c["not_persistent"] else "no")
                + "</td></tr>" for c in checks)
            detail = ('<table><thead><tr><th scope="col">Check</th><th scope="col">On</th><th scope="col">Failed</th>'
                      f'<th scope="col">Lost in the reboot</th></tr></thead><tbody>{table_rows}</tbody></table>')
        else:
            detail = ('<p class="muted">The checks of this task are not in the results any more (the session '
                      "folder was removed).</p>")
        body.append(f'<details class="task rise {_delay(i)}" id="task-{e(r.key)}"{" open" if i < 2 else ""}><summary>'
                    f'<span><span class="title">{e(r.title)}</span><br><span class="meta">{e(meta)}</span></span>'
                    f'{_bar(r.share)}<span class="share">{_pct(r.share)}</span><span class="last">{last}</span>'
                    f"</summary>{detail}</details>")
    return page("Tasks and checks", "/tasks", exam, exams_only, "\n".join(body), history.unreadable,
                heading=heading, lede=lede)


# --- one attempt ---------------------------------------------------------------------------------

def _status(status: str | None) -> str:
    if status is None:
        return '<span class="muted">not run</span>'
    if status == "pass":
        return '<span class="ok">✓ pass</span>'
    if status == "n/a":
        return '<span class="muted">n/a</span>'
    return f'<span class="bad">✗ {e(status)}</span>'


def attempt_page(results: dict[str, Any], domain_titles: dict[str, str]) -> str:
    r = results
    exam = r.get("exam") if r.get("exam") in EXAMS else "rhcsa"
    score = float(r.get("scaled_score", 0) or 0)
    total = int(r.get("total_points", TOTAL) or TOTAL)
    mark = int(r.get("pass_mark", PASS_MARK) or PASS_MARK)
    passed = bool(r.get("passed"))
    mode = str(r.get("mode", "exam"))
    graded = r.get("graded_at")
    title = f"{EXAMS[exam]} {mode}, {_day(graded)}"
    tasks = [t for t in r.get("tasks") or [] if isinstance(t, dict)]
    diff = score - mark
    verdict = ('<span class="pill ok">✓ Pass</span>' if passed else '<span class="pill bad">✗ Fail</span>')
    fill = 598 * min(max(score, 0), total) / total
    pm = 600 * mark / total
    head = [f'<p class="crumbs"><a href="/?{e(_query(exam, False))}">Overview</a> / {e(EXAMS[exam])} {e(mode)}, '
            f"{e(_day(graded, year=True))}</p>",
            f'<div class="intro"><div class="rise"><h1>{e(title)}</h1></div></div>',
            f'<div class="result rise d2"><div class="big">{score:.0f}<span> / {total}</span></div>{verdict}'
            f'<span class="muted">{abs(diff):.0f} {"above" if diff >= 0 else "below"} the pass mark of {mark}'
            "</span></div>",
            f'<svg class="scorebar" viewBox="0 0 600 34" role="img" aria-label="{score:.0f} of {total} points. '
            "The pass "
            f'mark is at {mark}."><rect class="track" x=".5" y=".5" width="599" height="13"/>'
            f'<rect class="fill {"pass" if passed else "fail"}" x="1" y="1" width="{fill:.1f}" height="12"/>'
            f'<line class="mark" x1="{pm:.1f}" y1="-2" x2="{pm:.1f}" y2="20"/>'
            f'<text x="{pm:.1f}" y="31">pass mark {mark}</text></svg>']
    used, allowed = r.get("elapsed_s"), r.get("duration_s")
    facts = [("Graded", f"{_day(graded, year=True)}, {_clock(graded)}"),
             ("Kind", f"{mode.capitalize()}, {len(tasks)} task{'s' * (len(tasks) != 1)}"),
             ("Time used", f"{_duration(used)} of {_duration(allowed)}" if mode == "exam" and used else "not timed"),
             ("Scoring", "Partial credit" if r.get("scoring") == "partial" else str(r.get("scoring", "")).capitalize())]
    if r.get("seed") not in (None, ""):
        facts.append(("Seed", str(r.get("seed"))))
    head.append('<dl class="facts">' + "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k, v in facts) + "</dl>")

    full = [t for t in tasks if float(t.get("points", 0) or 0) >= float(t.get("points_possible", 0) or 0) > 0]
    none = [t for t in tasks if float(t.get("points", 0) or 0) <= 0]
    part = [t for t in tasks if t not in full and t not in none]
    by_diff = r.get("by_difficulty") if isinstance(r.get("by_difficulty"), dict) else {}
    levels = [k for k in ("easy", "medium", "hard") if isinstance(by_diff.get(k), dict)]
    incidents = [i for i in r.get("incidents") or [] if isinstance(i, dict)]
    tiles = [("Full marks", f"{len(full)} task{'s' * (len(full) != 1)}", f"of {len(tasks)}"),
             ("Part of the points", f"{len(part)} task{'s' * (len(part) != 1)}",
              f"{sum(float(t.get('points', 0) or 0) for t in part):g} of "
              f"{sum(float(t.get('points_possible', 0) or 0) for t in part):g} points"),
             ("No points", f"{len(none)} task{'s' * (len(none) != 1)}",
              f"{sum(float(t.get('points_possible', 0) or 0) for t in none):g} points")]
    if levels:
        tiles.append((" · ".join(x.capitalize() if j == 0 else x for j, x in enumerate(levels)),
                      " · ".join(f"{float(by_diff[k].get('points', 0) or 0):.0f}" for k in levels),
                      "of " + " · ".join(f"{float(by_diff[k].get('possible', 0) or 0):g}" for k in levels)))
    tiles.append(("Incidents", str(len(incidents)) if incidents else "none",
                  "see below" if incidents else "no node needed help"))
    body = head + ["<section>" + _tiles(tiles)]
    lost = [str(t.get("number", "")) for t in tasks if t.get("not_persistent")]
    if lost:
        names = ", ".join(lost[:-1]) + (f" and {lost[-1]}" if len(lost) > 1 else lost[0])
        count = sum(len(t.get("not_persistent") or []) for t in tasks)
        body.append(f'<div class="callout"><div class="label">↻ Lost in the reboot</div><div>{count} answer'
                    f"{'s' * (count != 1)} worked before the grading reboot and not after it: "
                    f"task{'s' * (len(lost) != 1)} {e(names)}. They are marked ↻ below.</div></div>")
    if incidents:
        body.append('<div class="callout"><div class="label">Incidents</div><ul>' + "".join(
            f"<li><b>{e(i.get('node', ''))}</b>: {e(i.get('message', ''))}</li>" for i in incidents) + "</ul></div>")
    body.append("</section>")

    by_domain = r.get("by_domain") if isinstance(r.get("by_domain"), dict) else {}
    if by_domain:
        drows = "".join(
            f"<tr><td>{e(domain_titles.get(k, k))}</td><td class=\"r num\">{float(v.get('points', 0) or 0):g} / "
            f"{e(v.get('possible', 0))}</td>"
            f"<td>{_bar(float(v.get('points', 0) or 0) / float(v.get('possible') or 1), 200)}"
            "</td></tr>" for k, v in by_domain.items() if isinstance(v, dict))
        body.append('<section><h2>By objective domain</h2><div class="table-wrap"><table><thead><tr>'
                    '<th scope="col">Domain</th><th scope="col" class="r">Points</th><th scope="col">Share</th></tr>'
                    f"</thead><tbody>{drows}</tbody></table></div></section>")

    items = []
    for i, t in enumerate(tasks):
        pts, possible = float(t.get("points", 0) or 0), float(t.get("points_possible", 0) or 0)
        share = pts / possible if possible else None
        lost_ids = set(t.get("not_persistent") or [])
        post = [c for c in t.get("post") or [] if isinstance(c, dict)]
        pre = {(c.get("id"), c.get("node")): c for c in t.get("pre") or [] if isinstance(c, dict)}
        nodes = sorted({str(c.get("node")) for c in post if c.get("node")})
        rows = []
        for c in post:
            if c.get("status") == "n/a":
                continue
            before = pre.get((c.get("id"), c.get("node")))
            notes = []
            if c.get("guard"):
                notes.append("must not break")
            if c.get("id") in lost_ids:
                notes.append("↻ worked before the reboot")
            if c.get("status") != "pass" and c.get("detail"):
                notes.append(str(c["detail"]))
            rows.append(f'<tr><td>{e(c.get("desc", ""))}</td><td>{e(c.get("node", ""))}</td>'
                        f'<td class="nowrap">{_status(before.get("status") if before else None)}</td>'
                        f'<td class="nowrap">{_status(str(c.get("status", "")))}</td>'
                        f'<td>{e("; ".join(notes))}</td></tr>')
        table = ('<table><thead><tr><th scope="col">Check</th><th scope="col">On</th><th scope="col">Before the reboot'
                 '</th><th scope="col">After the reboot</th><th scope="col">Notes</th></tr></thead><tbody>'
                 + "".join(rows) + "</tbody></table>") if rows else '<p class="muted">No checks were recorded.</p>'
        items.append(f'<details class="task n rise {_delay(i)}"{" open" if lost_ids else ""}><summary>'
                     f'<span class="n">{e(t.get("number", ""))}</span><span><span class="title">{e(t.get("title", ""))}'
                     f'</span> <span class="meta">· {e(", ".join(nodes))} · {e(t.get("difficulty", ""))}</span></span>'
                     f'<span class="last">{_mark(share)} {pts:g} / {possible:g}{" ↻" if lost_ids else ""}</span>'
                     f"</summary>{table}</details>")
    body.append(f'<section><h2>The {len(tasks)} tasks</h2><p class="sub">In exam order. Open a task to see its checks. '
                "The same report is in the terminal:</p>"
                f'<div class="cmd"><span>$ </span>./autorelabel exam results {e(r.get("session", ""))}</div>'
                + "".join(items) + "</section>")
    return page(title, "", exam, False, "\n".join(body), filters=False)
