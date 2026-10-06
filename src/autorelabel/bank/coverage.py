"""Objective coverage: computation, the CI gate, and docs/COVERAGE.md."""

from __future__ import annotations

from dataclasses import dataclass, field

from .loader import Bank

GATES = ("none", "wave1", "full")
_BADGE = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}


@dataclass
class ObjectiveCoverage:
    id: str
    text: str
    domain: str
    implicit: bool
    tasks: list[str] = field(default_factory=list)
    primary_tasks: list[str] = field(default_factory=list)
    facets: dict[str, list[str]] = field(default_factory=dict)   # facet-id -> task ids
    optional_facets: set[str] = field(default_factory=set)


def compute(bank: Bank) -> list[ObjectiveCoverage]:
    out = []
    for d in bank.objectives.domains:
        for o in d.objectives:
            cov = ObjectiveCoverage(o.id, o.text, d.id, o.implicit)
            cov.facets = {f.id: [] for f in o.facets}
            cov.optional_facets = {f.id for f in o.facets if f.optional}
            for t in bank.tasks.values():
                if o.id in t.objectives:
                    cov.tasks.append(t.id)
                if t.primary == o.id:
                    cov.primary_tasks.append(t.id)
                for f in t.facets:
                    oid, fid = f.split(":", 1)
                    if oid == o.id and fid in cov.facets:
                        cov.facets[fid].append(t.id)
            out.append(cov)
    return out


def gate_failures(bank: Bank, level: str | None = None) -> list[str]:
    level = level or bank.blueprint.coverage_gate
    if level == "none":
        return []
    problems = []
    for c in compute(bank):
        if not c.primary_tasks and not (c.implicit and c.tasks):
            problems.append(f"{c.id}: no task has it as primary objective")
        if level == "full":
            if len(c.tasks) < 2:
                problems.append(f"{c.id}: only {len(c.tasks)} task(s); at least 2 required")
            for fid, tasks in c.facets.items():
                if not tasks and fid not in c.optional_facets:
                    problems.append(f"{c.id}:{fid}: facet not covered by any task")
    return problems


def summary(bank: Bank) -> dict[str, int]:
    cov = compute(bank)
    facets_total = sum(len(c.facets) for c in cov)
    facets_covered = sum(1 for c in cov for t in c.facets.values() if t)
    return {
        "objectives": len(cov),
        "objectives_with_primary": sum(1 for c in cov if c.primary_tasks or (c.implicit and c.tasks)),
        "objectives_with_2plus": sum(1 for c in cov if len(c.tasks) >= 2),
        "facets": facets_total,
        "facets_covered": facets_covered,
        "tasks": len(bank.tasks),
    }


def markdown(bank: Bank, verified: dict[str, str] | None = None) -> str:
    """Render docs/COVERAGE.md. `verified` maps task id -> self-test stamp."""
    verified = verified or {}
    s = summary(bank)
    lines = [
        f"# {bank.exam.upper()} objective coverage",
        "",
        f"Objectives are verbatim from Red Hat's exam page ({bank.objectives.source_url}),"
        f" checked {bank.objectives.source_checked}.",
        "Every objective line is split into independently testable *facets*.",
        "",
        f"- **{s['tasks']}** tasks",
        f"- **{s['objectives_with_primary']}/{s['objectives']}** objective lines have a primary task",
        f"- **{s['objectives_with_2plus']}/{s['objectives']}** objective lines have 2+ tasks",
        f"- **{s['facets_covered']}/{s['facets']}** facets covered",
        "",
        "Legend: 🟢 easy (10 pts) · 🟡 medium (15 pts) · 🔴 hard (20 pts) · ✅ self-tested on a real RHEL 10 VM",
        "",
    ]
    by_domain: dict[str, list[ObjectiveCoverage]] = {}
    for c in compute(bank):
        by_domain.setdefault(c.domain, []).append(c)
    for d in bank.objectives.domains:
        lines += [f"## {d.title}", ""]
        for c in by_domain.get(d.id, []):
            mark = "✅" if c.primary_tasks or (c.implicit and c.tasks) else "⬜"
            lines.append(f"### {mark} {c.text}")
            lines.append("")
            for fid, tasks in c.facets.items():
                facet = next(f for f in bank.objectives.objectives[c.id].facets if f.id == fid)
                if tasks:
                    refs = ", ".join(
                        f"{_BADGE[bank.tasks[t].difficulty]} `{t.split('.', 2)[2]}`"
                        + (" ✅" if t in verified else "") for t in tasks)
                    lines.append(f"- {facet.desc}: {refs}")
                else:
                    opt = " *(optional drill)*" if facet.optional else ""
                    lines.append(f"- {facet.desc}: *not yet covered*{opt}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
