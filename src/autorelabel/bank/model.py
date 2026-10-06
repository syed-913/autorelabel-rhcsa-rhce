"""Data model for objectives, tasks and blueprints."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DIFFICULTIES = ("easy", "medium", "hard")


@dataclass(frozen=True)
class Facet:
    id: str
    desc: str
    optional: bool = False


@dataclass(frozen=True)
class Objective:
    id: str
    text: str
    domain: str
    facets: tuple[Facet, ...]
    implicit: bool = False

    def facet_keys(self) -> list[str]:
        return [f"{self.id}:{f.id}" for f in self.facets]


@dataclass(frozen=True)
class Domain:
    id: str
    title: str
    objectives: tuple[Objective, ...]


@dataclass
class ObjectiveSet:
    exam: str
    source_url: str
    source_checked: str
    domains: tuple[Domain, ...]

    @property
    def objectives(self) -> dict[str, Objective]:
        return {o.id: o for d in self.domains for o in d.objectives}

    @property
    def facets(self) -> dict[str, Facet]:
        out = {}
        for o in self.objectives.values():
            for f in o.facets:
                out[f"{o.id}:{f.id}"] = f
        return out


@dataclass(frozen=True)
class Check:
    id: str
    desc: str
    run: str
    covers: tuple[str, ...]
    on: str | None = None          # node to run on; None = the task's node
    weight: float = 1.0
    timeout: int = 60


@dataclass(frozen=True)
class ParamSpec:
    name: str
    kind: str                       # choice | range | token | value | pool
    args: Any


@dataclass
class Task:
    id: str
    exam: str
    domain: str
    path: Path
    title: str
    primary: str
    objectives: tuple[str, ...]
    facets: tuple[str, ...]          # "objective-id:facet-id"
    difficulty: str
    estimated_minutes: int
    node: str
    prompt: str
    requirements: dict[str, str]
    checks: tuple[Check, ...]
    references: tuple[str, ...]
    params: dict[str, ParamSpec] = field(default_factory=dict)
    anchor: str | None = None
    exclusive: tuple[str, ...] = ()
    resources: dict[str, Any] = field(default_factory=dict)
    difficulty_reason: str = ""
    mistakes_na: str = ""
    notes: str = ""

    # scripts discovered on disk: node name -> path
    def scripts(self, stem: str) -> dict[str, Path]:
        out: dict[str, Path] = {}
        main = self.path / f"{stem}.sh"
        if main.exists():
            out[self.node] = main
        for p in sorted(self.path.glob(f"{stem}@*.sh")):
            out[p.stem.split("@", 1)[1]] = p
        return out

    @property
    def setup_scripts(self) -> dict[str, Path]:
        return self.scripts("setup")

    @property
    def solution_scripts(self) -> dict[str, Path]:
        return self.scripts("solution")

    def tests(self, kind: str) -> list[Path]:
        d = self.path / "tests"
        return sorted(d.glob(f"{kind}-*.sh")) if d.exists() else []

    @property
    def solution_md(self) -> Path:
        return self.path / "solution.md"

    @property
    def solution_yml(self) -> Path:
        return self.path / "solution.yml"


@dataclass
class Blueprint:
    exam: str
    tasks: int
    duration_minutes: int
    total_points: int
    pass_mark: int
    points: dict[str, int]
    difficulty_mix: dict[str, int]
    domains: dict[str, tuple[int, int]]
    require: list[list[str]]                 # each group: objective-id prefixes, ≥1 task must match
    anchors: list[str]
    coverage_gate: str = "none"              # none | wave1 | full

    def points_for(self, difficulty: str) -> int:
        return self.points[difficulty]
