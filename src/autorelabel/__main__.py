"""Entry point: `./autorelabel` (TUI) or `./autorelabel <command>` (CLI)."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    from . import cli

    return cli.main(argv)


if __name__ == "__main__":
    sys.exit(main())
