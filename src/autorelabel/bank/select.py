"""Seeded exam generation that always satisfies the blueprint.

Constraints: one of the blueprint's difficulty mixes, exactly (so the total is
always the blueprint's points), per-domain min/max, required objective groups,
anchor tasks, exclusive groups, and per-disk space budgets.

The generator looks ahead: a task is only added if the mix and every domain's
range can still be met with the tasks that are left (`_State.feasible`). Picking
first and rejecting the exams that don't come out right would favour whatever
makes an exam come out right, and with a tight blueprint that meant the same
few hard tasks in most exams and some tasks in practically none.

Among valid exams, tasks covering objectives you haven't been tested on recently
are preferred, and tasks of your last two exams are held back, which rotates
coverage across attempts without biasing toward weak areas.
"""

from __future__ import annotations

import datetime
import random
import string
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Any

from .. import labspec
from .loader import Bank
from .model import Task

MAX_ATTEMPTS = 3000
DISK_HEADROOM = 0.9
# A task of the previous exam is this much less likely to be picked early, one of the exam
# before that somewhat less: the next exam should not be the last one again. They stay
# possible, because a small bank cannot fill an exam without them.
SEEN_LAST_EXAM = 0.15
SEEN_EXAM_BEFORE = 0.5


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


def _weighted_order(tasks: list[Task], rng: random.Random, recency: dict[str, float],
                    seen: dict[str, float] | None = None) -> list[Task]:
    """Efraimidis-Spirakis weighted shuffle; weight grows for objectives not seen recently and
    shrinks for the tasks of the last exams (`seen`: task id -> factor)."""
    seen = seen or {}

    def key(t: Task) -> float:
        w = 1.0 + max((recency.get(o, 1.0) for o in t.objectives), default=1.0)
        return rng.random() ** (1.0 / (w * seen.get(t.id, 1.0)))
    return sorted(tasks, key=key, reverse=True)


def _matches(task: Task, prefixes: list[str]) -> bool:
    return any(o.startswith(p) for o in task.objectives for p in prefixes)


class _State:
    def __init__(self, bank: Bank, mix: dict[str, int], pool: list[Task]):
        self.bank = bank
        self.bp = bank.blueprint
        self.mix = mix
        self.chosen: list[Task] = []
        self.diff: Counter[str] = Counter()
        self.dom: Counter[str] = Counter()
        self.excl: set[str] = set()
        self.disk: Counter[str] = Counter()
        self.cap = _disk_capacity_mib(bank.exam)
        # what is left to pick from, per (domain, difficulty); anchors are placed first and
        # never picked again
        self.left: Counter[tuple[str, str]] = Counter((t.domain, t.difficulty) for t in pool if not t.anchor)
        self.levels = sorted(mix)
        self.subsets = [frozenset(c) for n in range(len(self.levels) + 1) for c in combinations(self.levels, n)]

    def feasible(self, t: Task | None = None) -> bool:
        """Can the exam still be completed (after adding `t`): the mix exactly, every domain
        within its range, counting only how many tasks are left per domain and difficulty?

        That is a small transportation problem: each domain must supply between its remaining
        minimum and maximum, each difficulty needs an exact number, and a domain has only so
        many tasks of each difficulty left. By Hoffman's circulation theorem it has a solution
        if and only if, for every set J of difficulties, the domains can supply at least what J
        needs, and are not forced to supply more than that. Exclusive groups and disk budgets
        are not counted here; they only cost the attempt when they bite at the very end."""
        diff, dom, left = self.diff, self.dom, self.left
        extra_dom = extra_diff = None
        if t is not None:
            extra_dom, extra_diff = t.domain, t.difficulty
        need = {d: self.mix.get(d, 0) - diff[d] - (1 if d == extra_diff else 0) for d in self.levels}
        if any(n < 0 for n in need.values()):
            return False
        domains = set(self.bp.domains) | {d for d, _ in left}
        rows = []
        for name in domains:
            lo, hi = self.bp.domains.get(name, (0, self.bp.tasks))
            have = dom[name] + (1 if name == extra_dom else 0)
            if have > hi:
                return False
            avail = {d: left[(name, d)] - (1 if (name == extra_dom and d == extra_diff and not t.anchor) else 0)
                     for d in self.levels}
            rows.append((max(lo - have, 0), hi - have, avail))
        for chosen in self.subsets:
            needed = sum(need[d] for d in chosen)
            can = must = 0
            for lo, hi, avail in rows:
                inside = sum(avail[d] for d in chosen)
                can += min(hi, inside)
                must += max(lo - (sum(avail.values()) - inside), 0)
            if not must <= needed <= can:
                return False
        return True

    def can_add(self, t: Task, as_anchor: bool = False) -> bool:
        if t in self.chosen or (t.anchor and not as_anchor):
            return False
        if self.diff[t.difficulty] >= self.mix.get(t.difficulty, 0):
            return False
        lo_hi = self.bp.domains.get(t.domain)
        if lo_hi and self.dom[t.domain] >= lo_hi[1]:
            return False
        if self.excl.intersection(t.exclusive):
            return False
        for disk, mib in (t.resources.get("disk") or {}).items():
            if self.disk[disk] + int(mib) > self.cap.get(disk, 0):
                return False
        return self.feasible(t)

    def add(self, t: Task) -> None:
        self.chosen.append(t)
        self.diff[t.difficulty] += 1
        self.dom[t.domain] += 1
        if not t.anchor:
            self.left[(t.domain, t.difficulty)] -= 1
        self.excl.update(t.exclusive)
        for disk, mib in (t.resources.get("disk") or {}).items():
            self.disk[disk] += int(mib)

    def valid(self) -> bool:
        if len(self.chosen) != self.bp.tasks:
            return False
        if any(self.diff[d] != n for d, n in self.mix.items()):
            return False
        for dom, (lo, hi) in self.bp.domains.items():
            if not lo <= self.dom[dom] <= hi:
                return False
        return all(any(_matches(t, group) for t in self.chosen) for group in self.bp.require)


def _attempt(bank: Bank, rng: random.Random, recency: dict[str, float],
             seen: dict[str, float] | None = None) -> list[Task] | None:
    pool = [t for t in bank.tasks.values() if not t.practice_only]
    st = _State(bank, rng.choice(bank.blueprint.difficulty_mixes), pool)
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
        for t in _weighted_order(cands, rng, recency, seen):
            if st.can_add(t):
                st.add(t)
                break
        else:
            return None
    # 3. everything else, in one weighted order. The domain minimums need no pass of their
    # own: can_add refuses a task once the slots that are left are all owed to other domains.
    for t in _weighted_order(regular, rng, recency, seen):
        if len(st.chosen) >= st.bp.tasks:
            break
        if st.can_add(t):
            st.add(t)
    return st.chosen if st.valid() else None


def seen_factors(previous_exams: list[list[str]]) -> dict[str, float]:
    """previous_exams: the task ids of earlier full exams, the latest first. Returns the factor
    for each task of the last two."""
    out: dict[str, float] = {}
    for tasks, factor in zip(previous_exams, (SEEN_LAST_EXAM, SEEN_EXAM_BEFORE), strict=False):
        for tid in tasks:
            out.setdefault(tid, factor)
    return out


def _order(bank: Bank, tasks: list[Task]) -> list[Task]:
    anchors = bank.blueprint.anchors
    domain_order = [d.id for d in bank.objectives.domains]

    def key(t: Task) -> tuple[int, int, str]:
        a = anchors.index(t.anchor) if t.anchor in anchors else len(anchors)
        d = domain_order.index(t.domain) if t.domain in domain_order else len(domain_order)
        return (a, d, t.id)

    return sorted(tasks, key=key)


def future_date(args: Any, rng: random.Random, today: datetime.date) -> str:
    """`[min, max]` days from today -> "YYYY-MM-DD"; `{days: [min, max], times: [...]}` adds
    " HH:MM". Relative to the exam's creation, so a task like scheduling an at job never asks
    for a date that has already passed."""
    days, times = (args["days"], args.get("times")) if isinstance(args, dict) else (args, None)
    day = (today + datetime.timedelta(days=rng.randint(int(days[0]), int(days[1])))).isoformat()
    return f"{day} {rng.choice(times)}" if times else day


def sweep_draws(task: Task) -> int:
    """Draws a parameter sweep needs so that every choice value of the task comes up once."""
    return max((len(spec.args) for spec in task.params.values() if spec.kind == "choice"), default=1)


def resolve_params(tasks: list[Task], pools: dict[str, list[Any]], rng: random.Random,
                   today: datetime.date | None = None, sweep: int | None = None) -> list[dict[str, Any]]:
    """Draw parameters. Pool draws are without replacement across the whole exam
    so two tasks never collide on a username, port, path, ...
    `sweep` (self-test parameter sweep): draw number i takes every choice's value i mod n
    instead of a random one, so draws 0..sweep_draws-1 cover all values."""
    today = today or datetime.date.today()
    remaining = {name: list(values) for name, values in pools.items()}
    for values in remaining.values():
        rng.shuffle(values)
    out = []
    for t in tasks:
        p: dict[str, Any] = {}
        for name, spec in t.params.items():
            if spec.kind == "choice":
                p[name] = rng.choice(spec.args) if sweep is None else spec.args[sweep % len(spec.args)]
            elif spec.kind == "range":
                p[name] = rng.randint(int(spec.args[0]), int(spec.args[1]))
            elif spec.kind == "token":
                p[name] = "".join(rng.choice(string.ascii_lowercase + string.digits) for _ in range(int(spec.args)))
            elif spec.kind == "value":
                p[name] = spec.args
            elif spec.kind == "future_date":
                p[name] = future_date(spec.args, rng, today)
            elif spec.kind == "pool":
                values = remaining.get(spec.args)
                if not values:
                    raise SelectionError(f"pool {spec.args!r} exhausted while preparing {t.id}")
                p[name] = values.pop()
        out.append(p)
    return out


def generate(bank: Bank, seed: int, recency: dict[str, float] | None = None,
             seen: dict[str, float] | None = None) -> list[SelectedTask]:
    """A full blueprint-valid exam for `seed` (deterministic for the same history).
    recency: objective id -> weight (objectives not tested recently weigh more).
    seen: task id -> factor below 1 for the tasks of the last exams (see `seen_factors`)."""
    recency = recency or {}
    for attempt in range(MAX_ATTEMPTS):
        rng = random.Random(f"{bank.exam}:{seed}:{attempt}")
        chosen = _attempt(bank, rng, recency, seen)
        if chosen:
            ordered = _order(bank, chosen)
            params = resolve_params(ordered, bank.pools, random.Random(f"{bank.exam}:{seed}:params"))
            return [SelectedTask(i + 1, t, p, bank.blueprint.points_for(t.difficulty))
                    for i, (t, p) in enumerate(zip(ordered, params, strict=True))]
    raise SelectionError(
        f"could not build a valid {bank.exam.upper()} exam from {len(bank.tasks)} tasks: "
        "the bank is too small for the blueprint (domain quotas / difficulty mix)."
    )


def practice(bank: Bank, task_ids: list[str], seed: int, sweep: int | None = None) -> list[SelectedTask]:
    """Practice set: the given tasks, in bank order, no blueprint constraints."""
    tasks = [bank.tasks[t] for t in task_ids]
    params = resolve_params(tasks, bank.pools, random.Random(f"{bank.exam}:{seed}:practice"), sweep=sweep)
    return [SelectedTask(i + 1, t, p, bank.blueprint.points_for(t.difficulty))
            for i, (t, p) in enumerate(zip(tasks, params, strict=True))]
