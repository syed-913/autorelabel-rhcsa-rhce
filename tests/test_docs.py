"""The user guide stays in step with the code."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from pathlib import Path

from autorelabel import cli

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "guide"


def _commands(parser: argparse.ArgumentParser, prefix: str = "") -> Iterator[str]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, sub in action.choices.items():
                if name == "proctor":                  # internal: started by the engine
                    continue
                yield prefix + name
                yield from _commands(sub, prefix + name + " ")


def test_every_command_is_in_the_command_reference():
    text = (GUIDE / "07-commands.md").read_text(encoding="utf-8")
    missing = [c for c in _commands(cli.build_parser()) if f"`{c}" not in text and f"autorelabel {c}" not in text]
    assert not missing, f"not in docs/guide/07-commands.md: {missing}"


def test_readme_and_guide_use_no_em_or_en_dashes():
    for page in [ROOT / "README.md", *GUIDE.glob("*.md")]:
        text = page.read_text(encoding="utf-8")
        assert "—" not in text and "–" not in text, page.name
