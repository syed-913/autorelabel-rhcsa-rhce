"""Seeded exam generation that always satisfies the blueprint.

Constraints: exact difficulty mix (so the total is always the blueprint's
points), per-domain min/max, required objective groups, anchor tasks, exclusive
groups, and per-disk space budgets. Among valid exams, tasks covering
objectives you haven't been tested on recently are preferred, which rotates
coverage across attempts without biasing toward weak areas.
"""

from __future__ import annotations

import random
import string
from collections import Counter
from dataclasses import dataclass
from typing import Any

from .. import labspec
from .loader import Bank
from .model import Task

MAX_ATTEMPTS = 3000
DISK_HEADROOM = 0.9


class SelectionError(RuntimeError):
    pass


@dataclass
class SelectedTask:
    number: int
    task: Task
    params: dict[str, Any]
    points: int

    def to_json(self) -> dict[str, Any]:
        return {"number": self.number, "task": self.task.id, "params": self.params, "points": self.points}


def _disk_capacity_mib(exam: str) -> dict[str, int]:
    cap = {}
    for vm in labspec.topology(exam, "lite"):
        for d in vm.disks:
            cap[f"{vm.name}.{d.name}"] = int(d.size_gb * 1024 * DISK_HEADROOM)
    return cap


def _weighted_order(tasks: list[Task], rng: random.Random, recency: dict[str, float]) -> list[Task]:
    """Efraimidis-Spirakis weighted shuffle; weight grows for objectives not seen recently."""
    def key(t: Task) -> float:
        w = 1.0 + max((recency.get(o, 1.0) for o in t.objectives), default=1.0)
        return rng.random() ** (1.0 / w)
    return sorted(tasks, key=key, reverse=True)


def _matches(task: Task, prefixes: list[str]) -> bool:
    return any(o.startswith(p) for o in task.objectives for p in prefixes)


class _State:
    def __init__(self, bank: Bank):
        self.bank = bank
        self.bp = bank.blueprint
        self.chosen: list[Task] = []
        self.diff: Counter[str] = Counter()
        self.dom: Counter[str] = Counter()
        self.excl: set[str] = set()
        self.disk: Counter[str] = Counter()
        self.cap = _disk_capacity_mib(bank.exam)

    def can_add(self, t: Task, as_anchor: bool = False) -> bool:
        if t in self.chosen or (t.anchor and not as_anchor):
            return False
        if self.diff[t.difficulty] >= self.bp.difficulty_mix.get(t.difficulty, 0):
            return False
        lo_hi = self.bp.domains.get(t.domain)
        if lo_hi and self.dom[t.domain] >= lo_hi[1]:
            return False
        if self.excl.intersection(t.exclusive):
            return False
        for disk, mib in (t.resources.get("disk") or {}).items():
            if self.disk[disk] + int(mib) > self.cap.get(disk, 0):
                return False
        return True

    def add(self, t: Task) -> None:
        self.chosen.append(t)
        self.diff[t.difficulty] += 1
        self.dom[t.domain] += 1
        self.excl.update(t.exclusive)
        for disk, mib in (t.resources.get("disk") or {}).items():
            self.disk[disk] += int(mib)

    def valid(self) -> bool:
        if len(self.chosen) != self.bp.tasks:
            return False
        if any(self.diff[d] != n for d, n in self.bp.difficulty_mix.items()):
            return False
        for dom, (lo, hi) in self.bp.domains.items():
            if not lo <= self.dom[dom] <= hi:
                return False
        return all(any(_matches(t, group) for t in self.chosen) for group in self.bp.require)


def _attempt(bank: Bank, rng: random.Random, recency: dict[str, float]) -> list[Task] | None:
    st = _State(bank)
    pool = [t for t in bank.tasks.values() if not t.practice_only]
    # 1. anchors
    for anchor in st.bp.anchors:
        variants = [t for t in pool if t.anchor == anchor and st.can_add(t, as_anchor=True)]
        if not variants:
            return None
        st.add(rng.choice(variants))
    regular = [t for t in pool if not t.anchor]
    # 2. required objective groups (e.g. "a Flatpak task", "an SELinux task")
    groups = list(st.bp.require)
    rng.shuffle(groups)
    for group in groups:
        if any(_matches(t, group) for t in st.chosen):
            continue
        cands = [t for t in regular if _matches(t, group)]
        for t in _weighted_order(cands, rng, recency):
            if st.can_add(t):
                st.add(t)
                break
        else:
            return None
    # 3. domain minimums
    domains = list(st.bp.domains.items())
    rng.shuffle(domains)
    for dom, (lo, _hi) in domains:
        cands = _weighted_order([t for t in regular if t.domain == dom], rng, recency)
        for t in cands:
            if st.dom[dom] >= lo:
                break
            if st.can_add(t):
                st.add(t)
        if st.dom[dom] < lo:
            return None
    # 4. fill the rest
    for t in _weighted_order(regular, rng, recency):
        if len(st.chosen) >= st.bp.tasks:
            break
        if st.can_add(t):
            st.add(t)
    return st.chosen if st.valid() else None


def _order(bank: Bank, tasks: list[Task]) -> list[Task]:
    anchors = bank.blueprint.anchors
    domain_order = [d.id for d in bank.objectives.domains]

    def key(t: Task) -> tuple[int, int, str]:
        a = anchors.index(t.anchor) if t.anchor in anchors else len(anchors)
        d = domain_order.index(t.domain) if t.domain in domain_order else len(domain_order)
        return (a, d, t.id)

    return sorted(tasks, key=key)


def resolve_params(tasks: list[Task], pools: dict[str, list[Any]], rng: random.Random) -> list[dict[str, Any]]:
    """Draw parameters. Pool draws are without replacement across the whole exam
    so two tasks never collide on a username, port, path, ..."""
    remaining = {name: list(values) for name, values in pools.items()}
    for values in remaining.values():
        rng.shuffle(values)
    out = []
    for t in tasks:
        p: dict[str, Any] = {}
        for name, spec in t.params.items():
            if spec.kind == "choice":
                p[name] = rng.choice(spec.args)
            elif spec.kind == "range":
                p[name] = rng.randint(int(spec.args[0]), int(spec.args[1]))
            elif spec.kind == "token":
                p[name] = "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(int(spec.args)))
            elif spec.kind == "value":
                p[name] = spec.args
            elif spec.kind == "pool":
                values = remaining.get(spec.args)
                if not values:
                    raise SelectionError(f"pool {spec.args!r} exhausted while preparing {t.id}")
                p[name] = values.pop()
        out.append(p)
    return out


def generate(bank: Bank, seed: int, recency: dict[str, float] | None = None) -> list[SelectedTask]:
    """A full blueprint-valid exam for `seed` (deterministic)."""
    recency = recency or {}
    for attempt in range(MAX_ATTEMPTS):
        rng = random.Random(f"{bank.exam}:{seed}:{attempt}")
        chosen = _attempt(bank, rng, recency)
        if chosen:
            ordered = _order(bank, chosen)
            params = resolve_params(ordered, bank.pools, random.Random(f"{bank.exam}:{seed}:params"))
            return [SelectedTask(i + 1, t, p, bank.blueprint.points_for(t.difficulty))
                    for i, (t, p) in enumerate(zip(ordered, params, strict=True))]
    raise SelectionError(
        f"could not build a valid {bank.exam.upper()} exam from {len(bank.tasks)} tasks: "
        "the bank is too small for the blueprint (domain quotas / difficulty mix)."
    )


def practice(bank: Bank, task_ids: list[str], seed: int) -> list[SelectedTask]:
    """Practice set: the given tasks, in bank order, no blueprint constraints."""
    tasks = [bank.tasks[t] for t in task_ids]
    params = resolve_params(tasks, bank.pools, random.Random(f"{bank.exam}:{seed}:practice"))
    return [SelectedTask(i + 1, t, p, bank.blueprint.points_for(t.difficulty))
            for i, (t, p) in enumerate(zip(tasks, params, strict=True))]
