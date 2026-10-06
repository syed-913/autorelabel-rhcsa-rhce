from __future__ import annotations

import sys

from .. import banner


def run_tui() -> int:
    sys.stdout.write(banner.render_ansi())
    return 0
