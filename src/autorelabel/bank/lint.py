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
VALID_NODES_RHCE = {vm.name for vm in labspec.topology("rhce", "standard")}
_WRITE_HINTS = re.compile(
    r"(^|[;&|]\s*)(rm|mv|cp|touch|mkdir|useradd|usermod|chmod|chown|systemctl\s+(start|stop|enable|disable|restart)"
    r"|dnf\s+(install|remove)|setenforce|firewall-cmd\s+--(add|remove))\b"
)


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
        if c.on is not None and c.on not in valid_nodes:
            err(f"check {c.id!r} runs on unknown node {c.on!r}")
        if c.weight <= 0:
            err(f"check {c.id!r} has non-positive weight")
        if _WRITE_HINTS.search(c.run):
            warn(f"check {c.id!r} looks like it modifies state; checks must be read-only")
    for r in task.requirements:
        if r not in covered:
            err(f"requirement {r} is not verified by any check")

    # --- placeholders
    ctx = {**_sample_params(task), "lab": labfacts.sample(task.exam)}
    texts = [("prompt", task.prompt), *[(f"requirement {k}", v) for k, v in task.requirements.items()],
             *[(f"check {c.id}", c.run) for c in task.checks], *[(f"check {c.id} desc", c.desc) for c in task.checks]]
    for label, text in texts:
        for ph in render.placeholders(text):
            try:
                render.lookup(ctx, ph)
            except render.RenderError:
                err(f"{label}: unknown placeholder {{{{{ph}}}}}")
    for name, spec in task.params.items():
        if spec.kind == "pool" and spec.args not in bank.pools:
            err(f"param {name!r} uses unknown pool {spec.args!r}")
        if spec.kind == "choice" and (not isinstance(spec.args, list) or not spec.args):
            err(f"param {name!r}: choice needs a non-empty list")
        if spec.kind == "range" and (not isinstance(spec.args, list) or len(spec.args) != 2):
            err(f"param {name!r}: range needs [min, max]")

    # --- anchors / exclusivity
    if task.anchor and task.anchor not in bank.blueprint.anchors:
        err(f"anchor {task.anchor!r} is not declared in the blueprint")

    # --- scripts and test suites
    if not task.solution_scripts:
        err("solution.sh is missing (needed for self-test)")
    if not task.solution_md.exists():
        err("solution.md is missing (explanation shown after grading)")
    for node in [*task.setup_scripts, *task.solution_scripts]:
        if node not in valid_nodes:
            err(f"script targets unknown node {node!r}")
    if not task.tests("mistake") and not task.mistakes_na:
        err("no common-mistake test (tests/mistake-*.sh) and no `mistakes_na` reason")
    for script in [*task.setup_scripts.values(), *task.solution_scripts.values(),
                   *task.tests("alt"), *task.tests("mistake")]:
        head = script.read_text(encoding="utf-8").splitlines()[:3]
        if not head or not head[0].startswith("#!"):
            err(f"{script.name}: missing shebang")
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
