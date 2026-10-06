"""The autorelabel banner: ANSI-Shadow style block letters with a red→gold
gradient, a dimmer 'shadow', and a compact fallback for narrow terminals."""

from __future__ import annotations

import os
import shutil
import sys

from . import __version__

# Glyphs are 6 rows tall. Block cells ("█") get the gradient; box-drawing cells
# form the drop shadow.
_GLYPHS: dict[str, tuple[str, ...]] = {
    "a": (" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"),
    "u": ("██╗   ██╗", "██║   ██║", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "t": ("████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "),
    "o": (" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "),
    "r": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"),
    "e": ("███████╗", "██╔════╝", "█████╗  ", "██╔══╝  ", "███████╗", "╚══════╝"),
    "l": ("██╗     ", "██║     ", "██║     ", "██║     ", "███████╗", "╚══════╝"),
    "b": ("██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██████╔╝", "╚═════╝ "),
}
WORD = "autorelabel"

_COMPACT = (
    "┏━┓╻ ╻╺┳╸┏━┓┏━┓┏━╸╻  ┏━┓┏┓ ┏━╸╻  ",
    "┣━┫┃ ┃ ┃ ┃ ┃┣┳┛┣╸ ┃  ┣━┫┣┻┓┣╸ ┃  ",
    "╹ ╹┗━┛ ╹ ┗━┛╹┗╸┗━╸┗━╸╹ ╹┗━┛┗━╸┗━╸",
)

TAGLINE = "RHCSA & RHCE practice exam simulator for RHEL 10"
MOTTO = "# touch /.autorelabel"

# Gradient stops: Red Hat red → warm orange → gold
_STOPS = ((0xCC, 0x00, 0x00), (0xEE, 0x22, 0x22), (0xFF, 0x6A, 0x2B), (0xFF, 0xA5, 0x2E), (0xFF, 0xD1, 0x5C))
SHADOW = (0x6E, 0x1E, 0x1E)


def big_lines() -> list[str]:
    rows = ["" for _ in range(6)]
    for ch in WORD:
        for i, part in enumerate(_GLYPHS[ch]):
            rows[i] += part
    return rows


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))  # type: ignore[return-value]


def gradient(pos: float) -> tuple[int, int, int]:
    pos = min(max(pos, 0.0), 1.0)
    seg = pos * (len(_STOPS) - 1)
    i = min(int(seg), len(_STOPS) - 2)
    return _lerp(_STOPS[i], _STOPS[i + 1], seg - i)


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def color_cells(lines: list[str]) -> list[list[tuple[str, tuple[int, int, int] | None]]]:
    """Per-character colours: gradient on blocks (with a slight diagonal), shadow on
    box-drawing characters, none on spaces."""
    width = max(len(line) for line in lines)
    out = []
    for r, line in enumerate(lines):
        row = []
        for c, ch in enumerate(line):
            if ch == " ":
                row.append((ch, None))
            elif ch == "█":
                row.append((ch, gradient((c + r * 1.5) / (width + 9))))
            else:
                row.append((ch, SHADOW))
        out.append(row)
    return out


def _supports_truecolor() -> bool:
    return os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")


def _ansi_fg(rgb: tuple[int, int, int], truecolor: bool) -> str:
    if truecolor:
        return "\x1b[38;2;{};{};{}m".format(*rgb)
    r, g, b = (round(x / 255 * 5) for x in rgb)
    return f"\x1b[38;5;{16 + 36 * r + 6 * g + b}m"


def render_ansi(width: int | None = None, color: bool | None = None) -> str:
    """Banner for plain terminals (CLI output)."""
    width = width or shutil.get_terminal_size((100, 24)).columns
    if color is None:
        color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    lines = big_lines() if width >= 92 else list(_COMPACT)
    if not color:
        body = "\n".join(lines)
        return f"{body}\n  {TAGLINE}  ·  v{__version__}\n  {MOTTO}\n"
    tc = _supports_truecolor()
    out = []
    for row in color_cells(lines):
        buf = []
        for ch, rgb in row:
            buf.append(ch if rgb is None else _ansi_fg(rgb, tc) + "\x1b[1m" + ch)
        out.append("".join(buf) + "\x1b[0m")
    out.append(f"  \x1b[1m{TAGLINE}\x1b[0m  \x1b[2m· v{__version__}\x1b[0m")
    out.append(f"  \x1b[2;3m{MOTTO}\x1b[0m")
    return "\n".join(out) + "\n"


def render_rich(width: int = 100):
    """Banner as a rich.text.Text (used by the TUI)."""
    from rich.text import Text

    lines = big_lines() if width >= 92 else list(_COMPACT)
    text = Text(no_wrap=True, overflow="crop")
    for i, row in enumerate(color_cells(lines)):
        for ch, rgb in row:
            text.append(ch, style=f"bold {_hex(rgb)}" if rgb else "")
        if i < len(lines) - 1:
            text.append("\n")
    return text
