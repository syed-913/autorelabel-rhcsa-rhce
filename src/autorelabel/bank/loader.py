"""Load objectives, blueprints and tasks from banks/<exam>/."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .. import paths
from .model import Blueprint, Check, Domain, Facet, Objective, ObjectiveSet, ParamSpec, Task

PARAM_KINDS = ("choice", "range", "token", "value", "pool", "future_date")


class BankError(ValueError):
    pass


class _BankLoader(yaml.SafeLoader):
    """YAML 1.2 booleans: only true/false. YAML 1.1 also reads on/off/yes/no as booleans, which
    would turn a check's `on: node2` key into `True` (and a `no` sshd value into False)."""


_BankLoader.yaml_implicit_resolvers = {
    first: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:bool"]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()}
_BankLoader.add_implicit_resolver("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"),
                                  list("tTfF"))


def _yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return yaml.load(fh, Loader=_BankLoader)  # a SafeLoader


def load_objectives(exam: str, root: Path | None = None) -> ObjectiveSet:
    root = root or paths.BANKS
    raw = _yaml(root / exam / "objectives.yaml")
    domains = []
    for d in raw["domains"]:
        objs = []
        for o in d["objectives"]:
            facets = tuple(Facet(f["id"], f.get("desc", ""), bool(f.get("optional", False)))
                           for f in o.get("facets", []))
            objs.append(Objective(o["id"], o["text"], d["id"], facets, bool(o.get("implicit", False))))
        domains.append(Domain(d["id"], d["title"], tuple(objs)))
    return ObjectiveSet(raw["exam"], raw.get("source_url", ""), str(raw.get("source_checked", "")), tuple(domains))


def load_blueprint(exam: str, root: Path | None = None) -> Blueprint:
    root = root or paths.BANKS
    raw = _yaml(root / exam / "blueprint.yaml")
    return Blueprint(
        exam=exam,
        tasks=int(raw["tasks"]),
        duration_minutes=int(raw["duration_minutes"]),
        total_points=int(raw["total_points"]),
        pass_mark=int(raw["pass_mark"]),
        points={k: int(v) for k, v in raw["points"].items()},
        difficulty_mix={k: int(v) for k, v in raw["difficulty_mix"].items()},
        domains={k: (int(v[0]), int(v[1])) for k, v in raw["domains"].items()},
        require=[list(g) for g in raw.get("require", [])],
        anchors=list(raw.get("anchors", [])),
        coverage_gate=str(raw.get("coverage_gate", "none")),
        practice_prereqs=list(raw.get("practice_prereqs", [])),
    )


def load_pools(exam: str, root: Path | None = None) -> dict[str, list[Any]]:
    root = root or paths.BANKS
    p = root / exam / "pools.yaml"
    if not p.exists():
        return {}
    return _yaml(p) or {}


def _param(name: str, spec: Any) -> ParamSpec:
    if not isinstance(spec, dict) or len(spec) != 1:
        raise BankError(f"param {name!r}: expected a single-key mapping like {{choice: [...]}}")
    kind, args = next(iter(spec.items()))
    if kind not in PARAM_KINDS:
        raise BankError(f"param {name!r}: unknown kind {kind!r}")
    return ParamSpec(name, kind, args)


def load_task(path: Path, exam: str) -> Task:
    """`path` is the task directory: banks/<exam>/tasks/<domain>/<slug>/"""
    raw = _yaml(path / "task.yaml") or {}
    domain, slug = path.parent.name, path.name
    task_id = f"{exam}.{domain}.{slug}"
    try:
        checks = tuple(
            Check(
                id=str(c["id"]),
                desc=str(c.get("desc", "")),
                run=str(c["run"]),
                covers=tuple(c.get("covers", [])),
                on=c.get("on"),
                weight=float(c.get("weight", 1)),
                timeout=int(c.get("timeout", 60)),
            )
            for c in raw.get("checks", [])
        )
        task = Task(
            id=task_id,
            exam=exam,
            domain=domain,
            path=path,
            title=str(raw["title"]),
            primary=str(raw["primary"]),
            objectives=tuple(raw.get("objectives") or [raw["primary"]]),
            facets=tuple(raw.get("facets", [])),
            difficulty=str(raw["difficulty"]),
            estimated_minutes=int(raw.get("estimated_minutes", 10)),
            node=str(raw.get("node", "node1")),
            prompt=str(raw["prompt"]).strip(),
            requirements={str(k): str(v) for k, v in (raw.get("requirements") or {}).items()},
            checks=checks,
            references=tuple(raw.get("references", [])),
            params={k: _param(k, v) for k, v in (raw.get("params") or {}).items()},
            anchor=raw.get("anchor"),
            exclusive=tuple(raw.get("exclusive", [])),
            resources=dict(raw.get("resources") or {}),
            difficulty_reason=str(raw.get("difficulty_reason", "")),
            mistakes_na=str(raw.get("mistakes_na", "")),
            notes=str(raw.get("notes", "")),
            breaks_boot=bool(raw.get("breaks_boot", False)),
            console_only=bool(raw.get("console_only", False)),
            practice_only=bool(raw.get("practice_only", False)),
        )
    except KeyError as exc:
        raise BankError(f"{task_id}: missing required field {exc}") from None
    if task.primary not in task.objectives:
        task.objectives = (task.primary, *task.objectives)
    return task


@dataclass
class Bank:
    exam: str
    objectives: ObjectiveSet
    blueprint: Blueprint
    tasks: dict[str, Task]
    pools: dict[str, list[Any]] = field(default_factory=dict)
    load_errors: list[str] = field(default_factory=list)


def load_bank(exam: str, root: Path | None = None) -> Bank:
    root = root or paths.BANKS
    errors: list[str] = []
    tasks: dict[str, Task] = {}
    tasks_dir = root / exam / "tasks"
    if tasks_dir.exists():
        for task_yaml in sorted(tasks_dir.glob("*/*/task.yaml")):
            try:
                t = load_task(task_yaml.parent, exam)
                tasks[t.id] = t
            except (BankError, yaml.YAMLError, TypeError, ValueError) as exc:
                errors.append(f"{task_yaml.parent.relative_to(root)}: {exc}")
    return Bank(exam, load_objectives(exam, root), load_blueprint(exam, root), tasks,
                load_pools(exam, root), errors)


@lru_cache(maxsize=4)
def cached_bank(exam: str) -> Bank:
    return load_bank(exam)
