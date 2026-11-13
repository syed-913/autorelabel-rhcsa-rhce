"""The Exam Desk: the exam in one browser window. The tasks beside terminals and consoles to the
lab nodes, and the clock, served on 127.0.0.1 by `./autorelabel desk` (see server.py), or from the
text interface's exam screen (w), which runs the same server in a thread of its own."""

from __future__ import annotations

import asyncio
import threading
from typing import Any

_running: list[Any] = []          # the desk the text interface started, at most one


def start_in_background(timeout: float = 15.0) -> Any:
    """The desk of this process, started in a thread if it isn't running yet. A running one is
    reused, never replaced: its shells live in it."""
    from .server import Desk

    if _running and _running[0].thread.is_alive():
        return _running[0]
    desk = Desk()
    ready = threading.Event()

    def main() -> None:
        asyncio.run(desk.run(lambda _d: ready.set()))

    desk.thread = threading.Thread(target=main, name="exam-desk", daemon=True)
    desk.thread.start()
    if not ready.wait(timeout):
        raise OSError("the Exam Desk did not start in time")
    _running[:] = [desk]
    return desk
