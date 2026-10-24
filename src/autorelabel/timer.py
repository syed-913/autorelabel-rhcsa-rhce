"""`./autorelabel exam timer`: the time left, in big digits, for a terminal next to your work
(the real exams keep a timer on screen). Read-only: the proctor keeps time, locks and grades."""

from __future__ import annotations

import shutil
import sys
import time

from . import session as S

# 3x5 bitmaps; every pixel is drawn two cells wide
_FONT = {
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"), "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "111"),
    ":": ("0", "1", "0", "1", "0"),
}
LOW, CRITICAL = 600, 120   # seconds: yellow, then red (as in the TUI)


def clock(seconds: float) -> str:
    seconds = int(max(0, seconds))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def big(text: str) -> list[str]:
    rows = ["" for _ in range(5)]
    for i, ch in enumerate(text):
        for r, bits in enumerate(_FONT[ch]):
            rows[r] += ("  " if i else "") + "".join("██" if b == "1" else "  " for b in bits)
    return rows


def status_line(sess: S.Session, now: float | None = None) -> tuple[str, str]:
    """(time text, state note) for a session."""
    if not sess.duration_s:
        return "untimed", "practice"
    if sess.state == S.READY:
        return clock(sess.duration_s), "not started yet"
    if sess.state == S.INTERRUPTED:
        return clock(sess.remaining(now)), "paused: the host restarted (./autorelabel resume)"
    if sess.state in (S.LOCKED, S.GRADING, S.GRADING_INTERRUPTED, S.GRADED):
        return "0:00:00", "time is up: the exam is locked" + (" and graded" if sess.state == S.GRADED else "")
    rem = sess.remaining(now)
    ends = time.strftime("%H:%M", time.localtime((now or time.time()) + rem))
    return clock(rem), f"ends about {ends}"


def once(sess: S.Session) -> int:
    text, note = status_line(sess)
    print(text if text != "untimed" else note)
    return 0


def run(session_id: str, compact: bool = False) -> int:
    tty = sys.stdout.isatty()
    warned: set[int] = set()
    shown = None
    out = sys.stdout
    if tty and not compact:
        out.write("\x1b[?25l\x1b[2J")          # hide the cursor, clear once
    try:
        while True:
            sess = S.load(session_id)
            text, note = status_line(sess)
            rem = sess.remaining() if sess.state == S.IN_PROGRESS and sess.duration_s else None
            color = "" if not tty or rem is None else "\x1b[31;1m" if rem <= CRITICAL else (
                "\x1b[33;1m" if rem <= LOW else "\x1b[1m")
            off = "\x1b[0m" if color else ""
            if rem is not None:
                for m in sorted(sess.warnings_minutes, reverse=True):
                    if rem <= m * 60 and m not in warned:
                        warned.add(m)
                        out.write("\a")
            title = f"{sess.exam.upper()} {'EXAM' if sess.mode == 'exam' else 'PRACTICE'}"
            width = shutil.get_terminal_size((80, 24)).columns
            if compact or not tty or width < 50:
                line = f"{title}  {text}  {note}"
                if tty:
                    out.write(f"\r\x1b[2K{color}{line}{off}")
                elif line != shown:
                    out.write(line + "\n")
                shown = line
            else:
                rows = big(text) if text != "untimed" else []
                frame = [title, "", *rows, "", note, "", "Ctrl+C closes this timer; the exam keeps running."]
                pad = " " * max(0, (width - max(len(r) for r in frame)) // 2)
                body = "\n".join(f"\x1b[2K{pad}{color if r in rows else ''}{r}{off if r in rows else ''}"
                                 for r in frame)
                if isinstance(shown, tuple) and shown[0] != width:
                    out.write("\x1b[2J")          # resized: no leftovers at the old position
                if (width, text, note) != shown:
                    out.write("\x1b[H" + body)
                shown = (width, text, note)
            out.flush()
            if sess.state not in (S.READY, S.IN_PROGRESS, S.INTERRUPTED):
                if tty and (compact or width < 50):
                    out.write("\n")
                return 0
            time.sleep(1.0 - time.time() % 1.0)
    except KeyboardInterrupt:
        return 0
    finally:
        if tty and not compact:
            out.write("\x1b[?25h\n")
            out.flush()
