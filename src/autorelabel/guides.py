"""Distro-specific install guidance (data in data/distro-guides.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import yaml

from . import hostinfo, paths


@dataclass(frozen=True)
class Step:
    key: str
    title: str
    run: tuple[str, ...]
    undo: tuple[str, ...]
    note: str = ""
    needs: tuple[str, ...] = ()


@lru_cache(maxsize=1)
def _data() -> dict:
    with open(paths.DATA / "distro-guides.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def family(distro: hostinfo.Distro | None = None) -> str:
    distro = distro or hostinfo.distro()
    families = _data()["families"]
    ids = (distro.id, *distro.like)
    for ident in ids:
        for name, fam in families.items():
            if ident in fam.get("match", []):
                return name
    return "generic"


def family_name(fam: str | None = None) -> str:
    return _data()["families"][fam or family()]["name"]


def step(key: str, fam: str | None = None) -> Step | None:
    fam = fam or family()
    steps = _data()["families"][fam]["steps"]
    raw = steps.get(key) or _data()["families"]["generic"]["steps"].get(key)
    if raw is None:
        return None
    return Step(
        key=key,
        title=raw.get("title", key),
        run=tuple(raw.get("run", [])),
        undo=tuple(raw.get("undo", [])),
        note=raw.get("note", ""),
        needs=tuple(raw.get("needs", [])),
    )


def with_prerequisites(key: str, fam: str | None = None) -> list[Step]:
    """A step plus the steps it needs (e.g. packer needs the HashiCorp repo)."""
    out: list[Step] = []
    seen: set[str] = set()

    def visit(k: str) -> None:
        if k in seen:
            return
        seen.add(k)
        s = step(k, fam)
        if s is None:
            return
        for dep in s.needs:
            visit(dep)
        out.append(s)

    visit(key)
    return out


def link(name: str) -> str:
    return _data()["links"].get(name, "")
