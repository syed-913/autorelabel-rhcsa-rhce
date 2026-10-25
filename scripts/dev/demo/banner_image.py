"""The README banner and the GitHub social preview, drawn from the TUI banner's real glyphs.

    python3 scripts/dev/demo/banner_image.py

Writes docs/media/banner.png (2560x1280, the README header at 2x) and docs/social-preview.png
(1280x640, GitHub's social preview size). Needs Pillow (python3-pil), Noto Sans and JetBrains Mono.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from autorelabel import banner  # noqa: E402

FONTS = Path.home() / ".local/share/fonts"
MONO_REG = str(FONTS / "JetBrainsMono-Regular.ttf")
SANS_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
SANS = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
OUTPUTS = {ROOT / "docs" / "media" / "banner.png": 2, ROOT / "docs" / "social-preview.png": 1}
SUPERSAMPLE = 2

S = 1                      # pixels per layout unit while drawing (the layout is 1280x640 units)
W, H = 1280, 640


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size * S)


def background() -> Image.Image:
    img = Image.new("RGB", (W, H), (8, 8, 10))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((W * 0.12, -H * 0.25, W * 0.88, H * 0.62), fill=(70, 8, 8))
    glow = glow.filter(ImageFilter.GaussianBlur(160 * S))
    return Image.blend(img, glow, 0.85)


def box_char(d: ImageDraw.ImageDraw, ch: str, x: float, y: float, cw: float, chh: float, rgb) -> None:
    """The banner's double-line shadow glyphs, drawn as lines so the cells join exactly."""
    cx, cy, gap, t = x + cw / 2, y + chh / 2, cw * 0.17, max(1, round(cw * 0.13))
    L, R, T, B = x, x + cw, y, y + chh
    segs = {
        "═": [((L, cy - gap), (R, cy - gap)), ((L, cy + gap), (R, cy + gap))],
        "║": [((cx - gap, T), (cx - gap, B)), ((cx + gap, T), (cx + gap, B))],
        "╗": [((L, cy - gap), (cx + gap, cy - gap)), ((cx + gap, cy - gap), (cx + gap, B)),
              ((L, cy + gap), (cx - gap, cy + gap)), ((cx - gap, cy + gap), (cx - gap, B))],
        "╔": [((cx - gap, cy - gap), (R, cy - gap)), ((cx - gap, cy - gap), (cx - gap, B)),
              ((cx + gap, cy + gap), (R, cy + gap)), ((cx + gap, cy + gap), (cx + gap, B))],
        "╚": [((cx - gap, T), (cx - gap, cy + gap)), ((cx - gap, cy + gap), (R, cy + gap)),
              ((cx + gap, T), (cx + gap, cy - gap)), ((cx + gap, cy - gap), (R, cy - gap))],
        "╝": [((cx + gap, T), (cx + gap, cy + gap)), ((L, cy + gap), (cx + gap, cy + gap)),
              ((cx - gap, T), (cx - gap, cy - gap)), ((L, cy - gap), (cx - gap, cy - gap))],
    }[ch]
    for a, b in segs:
        d.line((a, b), fill=rgb, width=t)


def centered(d: ImageDraw.ImageDraw, y: float, parts: list[tuple[str, ImageFont.FreeTypeFont, tuple]]) -> None:
    total = sum(d.textlength(t, font=f) for t, f, _ in parts)
    x = (W - total) / 2
    for text, f, rgb in parts:
        d.text((x, y), text, font=f, fill=rgb)
        x += d.textlength(text, font=f)


def render(scale: int) -> Image.Image:
    """The image at `scale` times 1280x640, drawn supersampled and then downscaled."""
    global S, W, H
    S = scale * SUPERSAMPLE
    W, H = 1280 * S, 640 * S
    img = background()
    d = ImageDraw.Draw(img)

    # the banner, cell by cell
    cells = banner.color_cells(banner.big_lines())
    cols = max(len(r) for r in cells)
    cw, chh = 12.4 * S, 24 * S
    x0, y0 = (W - cols * cw) / 2, 92 * S
    for r, row in enumerate(cells):
        for c, (ch, rgb) in enumerate(row):
            if rgb is None:
                continue
            x, y = x0 + c * cw, y0 + r * chh
            if ch == "█":
                d.rectangle((x, y, x + cw + 0.5, y + chh + 0.5), fill=rgb)
            else:
                box_char(d, ch, x, y, cw, chh, banner.SHADOW)

    # a gradient rule under the banner
    ry, rw = 270 * S, 720 * S
    for i in range(int(rw)):
        rgb = banner.gradient(i / rw)
        d.line(((W - rw) / 2 + i, ry, (W - rw) / 2 + i, ry + 2 * S), fill=rgb)

    white, grey, gold, dim = (245, 245, 245), (190, 190, 196), (255, 196, 84), (120, 120, 128)
    centered(d, 300 * S, [("RHCSA & RHCE practice exams on real RHEL 10 VMs", font(SANS_BOLD, 44), white)])
    sep = ("   ·   ", font(SANS, 26), dim)
    centered(d, 376 * S, [("20", font(SANS_BOLD, 26), gold), (" tasks", font(SANS, 26), grey), sep,
                          ("300", font(SANS_BOLD, 26), gold), (" points", font(SANS, 26), grey), sep,
                          ("pass at ", font(SANS, 26), grey), ("210", font(SANS_BOLD, 26), gold), sep,
                          ("graded after a reboot", font(SANS, 26), grey)])

    # a terminal line
    mono = font(MONO_REG, 26)
    prompt, cmd = "sh-5.2# ", "touch /.autorelabel"
    tw = d.textlength(prompt + cmd, font=mono) + 16 * S
    bx0, by0 = (W - tw) / 2 - 28 * S, 452 * S
    bx1, by1 = (W + tw) / 2 + 28 * S, by0 + 64 * S
    d.rounded_rectangle((bx0, by0, bx1, by1), radius=12 * S, fill=(18, 18, 21), outline=(52, 52, 58), width=S)
    tx, ty = bx0 + 28 * S, by0 + 14 * S
    d.text((tx, ty), prompt, font=mono, fill=(238, 64, 54))
    tx += d.textlength(prompt, font=mono)
    d.text((tx, ty), cmd, font=mono, fill=white)
    tx += d.textlength(cmd, font=mono) + 6 * S
    d.rectangle((tx, ty + 4 * S, tx + 13 * S, ty + 32 * S), fill=(255, 165, 46))

    centered(d, 572 * S, [("Linux hosts  ·  libvirt/KVM or VirtualBox  ·  free and open source (MIT)",
                           font(SANS, 21), dim)])
    return img.resize((W // SUPERSAMPLE, H // SUPERSAMPLE), Image.LANCZOS)


def main() -> None:
    for out, scale in OUTPUTS.items():
        render(scale).save(out, optimize=True)
        print(out.relative_to(ROOT), out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
