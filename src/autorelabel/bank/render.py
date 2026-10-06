"""Minimal, strict template rendering: {{ name }} or {{ lab.node1.ip }}.

Deliberately not Jinja: task text must stay simple, and an unknown placeholder
is an error (caught by the linter) rather than an empty string in an exam.
"""

from __future__ import annotations

import re
from typing import Any

PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)\s*\}\}")


class RenderError(KeyError):
    pass


def lookup(ctx: dict[str, Any], dotted: str) -> Any:
    cur: Any = ctx
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise RenderError(dotted)
    return cur


def render(text: str, ctx: dict[str, Any]) -> str:
    return PLACEHOLDER.sub(lambda m: str(lookup(ctx, m.group(1))), text)


def placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text))


def env_for(params: dict[str, Any], lab: dict[str, Any] | None = None) -> dict[str, str]:
    """Parameters as environment variables for setup/check/solution scripts:
    P_<NAME>=value, plus flattened lab facts as LAB_<PATH>=value."""
    env: dict[str, str] = {}

    def flatten(prefix: str, obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                flatten(f"{prefix}_{k.upper()}", v)
        else:
            env[prefix] = str(obj)

    for k, v in params.items():
        flatten(f"P_{k.upper()}", v)       # dict parameters become P_NAME_FIELD
    if lab:
        flatten("LAB", lab)
    return env
