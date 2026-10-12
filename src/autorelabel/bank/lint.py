"""Bank linter: schema, scope lock, requirement↔check traceability, placeholders,
scripts and test suites. Errors block a task from shipping."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .. import labfacts, labspec
from . import render
from .loader import Bank
from .model import DIFFICULTIES, Task

VALID_NODES_RHCSA = {vm.name for vm in labspec.topology("rhcsa", "standard")}
# RHCE tasks must work in both profiles: single nodes from the smaller (lite) lab, or @groups.
VALID_NODES_RHCE = {vm.name for vm in labspec.topology("rhce", "lite")}
VALID_GROUPS_RHCE = {f"@{g}" for g in labfacts.sample("rhce", "lite")["groups"]}
_WRITE_HINTS = re.compile(
    r"(^|[;&|]\s*)(rm|mv|cp|touch|mkdir|useradd|usermod|chmod|chown|systemctl\s+(start|stop|enable|disable|restart)"
    r"|dnf\s+(install|remove)|setenforce|firewall-cmd\s+--(add|remove))\b"
)


_HEREDOC = re.compile(r"<<-?\s*'?\"?([A-Za-z_]+)'?\"?")


def errexit_hazards(script: str) -> list[str]:
    """Lines whose failure `set -e` would NOT catch when they are not the last line:
    a negated command (`! cmd`) or a test/systemctl/sudo `&&` list. They must end with
    `|| exit 1` (or be split), or a failing line could be ignored."""
    body: list[tuple[int, str]] = []
    term = None
    for i, raw in enumerate(script.splitlines()):
        if term:
            if raw.strip() == term:
                term = None
            continue
        m = _HEREDOC.search(raw)
        if m:
            term = m.group(1)
        body.append((i, raw))
    nonempty = [i for i, raw in body if raw.strip()]
    last = nonempty[-1] if nonempty else -1
    bad = []
    for i, raw in body:
        st = raw.strip()
        if not st or i == last or st.endswith("|| exit 1") or st.endswith("\\") or st.startswith("#"):
            continue
        if st.startswith(("if ", "elif ", "while ", "until ", "for ", "case ")):
            continue
        if st.startswith("! ") or (re.match(r"(test |systemctl |sudo |\[ )", st) and " && " in st):
            bad.append(st)
        if re.search(r";\s*rc=\$\?", st):
            bad.append(st)
    return bad


_PIPE_INTO = r"(?<![|])[|](?![|])\s*"
_EARLY_EXIT = re.compile(_PIPE_INTO + r"(head\b|grep\b[^|]*?\s(-[a-zA-Z]*m|--max-count))")
_EARLY_EXIT_QUIET = re.compile(_PIPE_INTO + r"grep\b[^|]*?\s(-[a-zA-Z]*q|--quiet|--silent)")


def early_exit_pipes(script: str, *, quiet_grep_ok: bool) -> list[str]:
    """Lines that pipe into a reader that stops early (`head`, `grep -m`, and in scripts
    `grep -q`): the writer may then die of SIGPIPE, which pipefail turns into a failure, now and
    then. Use `sed -n 1p` (reads to the end) or a here-string. Checks may use `grep -q`, which
    check-lib makes drain the pipe."""
    bad, term = [], None
    for raw in script.splitlines():
        if term:
            if raw.strip() == term:
                term = None
            continue
        m = _HEREDOC.search(raw)
        if m:
            term = m.group(1)
        st = re.sub(r"\s#\s.*$", "", raw.strip())     # drop a trailing comment
        if st.startswith("#"):
            continue
        if _EARLY_EXIT.search(st) or (not quiet_grep_ok and _EARLY_EXIT_QUIET.search(st)):
            bad.append(st)
    return bad


@dataclass(frozen=True)
class Issue:
    severity: str        # error | warning
    task: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity.upper():7} {self.task}: {self.message}"


def _sample_params(task: Task) -> dict[str, object]:
    out: dict[str, object] = {}
    for name, spec in task.params.items():
        if spec.kind == "choice" or spec.kind == "range":
            out[name] = spec.args[0]
        elif spec.kind == "token":
            out[name] = "x" * int(spec.args)
        elif spec.kind == "value":
            out[name] = spec.args
        elif spec.kind == "pool":
            out[name] = f"<{spec.args}>"
        elif spec.kind == "future_date":
            out[name] = "2030-01-15 09:30" if isinstance(spec.args, dict) else "2030-01-15"
    return out


def lint_task(task: Task, bank: Bank) -> list[Issue]:
    issues: list[Issue] = []

    def err(msg: str) -> None:
        issues.append(Issue("error", task.id, msg))

    def warn(msg: str) -> None:
        issues.append(Issue("warning", task.id, msg))

    objectives = bank.objectives.objectives
    facets = bank.objectives.facets

    # --- scope lock
    if task.primary not in objectives:
        err(f"primary objective {task.primary!r} is not an official objective")
    for o in task.objectives:
        if o not in objectives:
            err(f"objective {o!r} is not an official objective")
    if task.primary in objectives and objectives[task.primary].domain != task.domain:
        err(f"task lives in domain {task.domain!r} but its primary objective is in "
            f"{objectives[task.primary].domain!r}")
    if not task.facets:
        err("no facets listed")
    for f in task.facets:
        if f not in facets:
            err(f"facet {f!r} does not exist")
        elif f.split(":", 1)[0] not in task.objectives:
            err(f"facet {f!r} belongs to an objective not listed in `objectives`")

    # --- basics
    if task.difficulty not in DIFFICULTIES:
        err(f"difficulty must be one of {DIFFICULTIES}")
    if not task.difficulty_reason:
        warn("difficulty_reason is empty (why does this task meet the rubric?)")
    valid_nodes = VALID_NODES_RHCSA if task.exam == "rhcsa" else VALID_NODES_RHCE
    if task.node not in valid_nodes:
        err(f"node {task.node!r} is not part of the {task.exam} lab")
    if not task.references:
        err("no references (official docs or man pages)")
    if task.estimated_minutes <= 0 or task.estimated_minutes > 60:
        warn("estimated_minutes looks wrong")

    # --- traceability
    if not task.requirements:
        err("no requirements listed")
    if not task.checks:
        err("no checks")
    elif all(c.guard is True for c in task.checks):
        err("every check is a guard: at least one check must verify the work itself")
    covered: set[str] = set()
    seen_ids: set[str] = set()
    for c in task.checks:
        if c.id in seen_ids:
            err(f"duplicate check id {c.id!r}")
        seen_ids.add(c.id)
        if not c.covers:
            err(f"check {c.id!r} covers no requirement")
        for r in c.covers:
            if r not in task.requirements:
                err(f"check {c.id!r} covers unknown requirement {r!r}")
            covered.add(r)
        groups = VALID_GROUPS_RHCE if task.exam == "rhce" else set()
        if c.on is not None and c.on not in valid_nodes and c.on not in groups:
            err(f"check {c.id!r} runs on unknown node {c.on!r}")
        if c.weight <= 0:
            err(f"check {c.id!r} has non-positive weight")
        if not isinstance(c.guard, bool):
            err(f"check {c.id!r}: guard must be true or false")
        if _WRITE_HINTS.search(c.run):
            warn(f"check {c.id!r} looks like it modifies state; checks must be read-only")
        for line in errexit_hazards(c.run):
            err(f"check {c.id!r}: a failure of this line would be ignored (append '|| exit 1'): {line[:80]}")
        for line in early_exit_pipes(c.run, quiet_grep_ok=True):
            err(f"check {c.id!r}: piping into head / grep -m can kill the writer (SIGPIPE + pipefail); "
                f"use sed -n 1p or a here-string: {line[:80]}")
    for r in task.requirements:
        if r not in covered:
            err(f"requirement {r} is not verified by any check")

    # --- placeholders
    texts = [("prompt", task.prompt), *[(f"requirement {k}", v) for k, v in task.requirements.items()],
             *[(f"check {c.id}", c.run) for c in task.checks], *[(f"check {c.id} desc", c.desc) for c in task.checks]]
    if task.solution_md.exists():
        texts.append(("solution.md", task.solution_md.read_text(encoding="utf-8")))
    reported: set[str] = set()
    for profile in ("standard", "lite"):
        ctx = {**_sample_params(task), "lab": labfacts.sample(task.exam, profile)}
        for label, text in texts:
            for ph in render.placeholders(text):
                try:
                    render.lookup(ctx, ph)
                except render.RenderError:
                    if (label, ph) not in reported:
                        reported.add((label, ph))
                        err(f"{label}: unknown placeholder {{{{{ph}}}}} ({profile} profile)")
    for name, spec in task.params.items():
        if spec.kind == "pool" and spec.args not in bank.pools:
            err(f"param {name!r} uses unknown pool {spec.args!r}")
        if spec.kind == "choice" and (not isinstance(spec.args, list) or not spec.args):
            err(f"param {name!r}: choice needs a non-empty list")
        if spec.kind == "range" and (not isinstance(spec.args, list) or len(spec.args) != 2):
            err(f"param {name!r}: range needs [min, max]")
        if spec.kind == "future_date":
            fd = spec.args if isinstance(spec.args, dict) else {"days": spec.args}
            days, times = fd.get("days"), fd.get("times", ["00:00"])
            if (not isinstance(days, list) or len(days) != 2 or not all(isinstance(d, int) for d in days)
                    or not 1 <= days[0] <= days[1] or set(fd) - {"days", "times"}
                    or not isinstance(times, list) or not times
                    or not all(isinstance(t, str) and re.fullmatch(r"[0-2]\d:[0-5]\d", t) for t in times)):
                err(f"param {name!r}: future_date needs [min, max] days (min >= 1), "
                    "or {days: [min, max], times: [HH:MM, ...]}")

    # --- anchors / exclusivity
    if task.anchor and task.anchor not in bank.blueprint.anchors:
        err(f"anchor {task.anchor!r} is not declared in the blueprint")

    # --- scripts and test suites
    if not task.solution_scripts:
        err("solution.sh is missing (needed for self-test)")
    if not task.solution_md.exists():
        err("solution.md is missing (explanation shown after grading)")
    for stem in ("setup", "solution"):
        if (task.path / f"{stem}.sh").exists() and (task.path / f"{stem}@{task.node}.sh").exists():
            err(f"{stem}.sh and {stem}@{task.node}.sh both target {task.node} (the task's node); only one "
                f"would run. Name scripts for other nodes {stem}@<node>.sh")
    script_groups = {g[1:] for g in VALID_GROUPS_RHCE} if task.exam == "rhce" else set()
    for node in [*task.setup_scripts, *task.solution_scripts]:
        if node not in valid_nodes and node not in script_groups:
            err(f"script targets unknown node {node!r}")
    if not task.tests("mistake") and not task.mistakes_na:
        err("no common-mistake test (tests/mistake-*.sh) and no `mistakes_na` reason")
    for script in [*task.setup_scripts.values(), *task.solution_scripts.values(),
                   *task.tests("alt"), *task.tests("mistake")]:
        text = script.read_text(encoding="utf-8")
        if not text.startswith("#!"):
            err(f"{script.name}: missing shebang")
        for line in early_exit_pipes(text, quiet_grep_ok=False):
            err(f"{script.name}: piping into head / grep -q / grep -m can kill the writer (SIGPIPE + "
                f"pipefail); use sed -n 1p or a here-string: {line[:80]}")
    return issues


def lint_bank(bank: Bank) -> list[Issue]:
    issues = [Issue("error", "bank", e) for e in bank.load_errors]
    # blueprint sanity
    bp = bank.blueprint
    total = sum(bp.points[d] * n for d, n in bp.difficulty_mix.items())
    if total != bp.total_points:
        issues.append(Issue("error", "blueprint", f"difficulty mix gives {total} points, expected {bp.total_points}"))
    if sum(bp.difficulty_mix.values()) != bp.tasks:
        issues.append(Issue("error", "blueprint", "difficulty mix does not add up to the task count"))
    domain_ids = {d.id for d in bank.objectives.domains}
    for dom in bp.domains:
        if dom not in domain_ids:
            issues.append(Issue("error", "blueprint", f"unknown domain {dom!r}"))
    for t in bank.tasks.values():
        issues.extend(lint_task(t, bank))
    anchors_seen = {t.anchor for t in bank.tasks.values() if t.anchor}
    for a in bp.anchors:
        if a not in anchors_seen and bank.tasks:
            issues.append(Issue("error", "blueprint", f"anchor {a!r} has no task"))
    return issues
