"""Minimal, strict template rendering: {{name}} or {{lab.node1.ip}} (no spaces).

Deliberately not Jinja: task text must stay simple, and an unknown placeholder
is an error (caught by the linter) rather than an empty string in an exam.
Ansible/Jinja expressions are written the usual way, with spaces (`{{ item }}`),
and are left untouched, so RHCE tasks can show playbooks and templates verbatim.
"""

from __future__ import annotations

import re
from typing import Any

PLACEHOLDER = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)\}\}")


class RenderError(KeyError):
    pass


def lookup(ctx: dict[str, Any], dotted: str) -> Any:
    cur: Any = ctx
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
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
        elif isinstance(obj, list):             # P_NAME="a b", P_NAME_0=a, P_NAME_1=b
            env[prefix] = " ".join(str(v) for v in obj)
            for i, v in enumerate(obj):
                flatten(f"{prefix}_{i}", v)
        else:
            env[prefix] = str(obj)

    for k, v in params.items():
        flatten(f"P_{k.upper()}", v)       # dict parameters become P_NAME_FIELD
    if lab:
        flatten("LAB", lab)
    return env
