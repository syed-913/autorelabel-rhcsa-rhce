"""The README demo animation, made with Manim Community (0.19 or newer): see render.sh.

Every scene starts and ends on black; render.sh renders them and joins them.
The banner uses the real glyphs and colours from src/autorelabel/banner.py, and the exam content
(task text, checks, lab names and addresses) is real bank content.
"""

from __future__ import annotations

import random
import re
import sys
from itertools import pairwise
from pathlib import Path

import numpy as np
from manim import (
    DEGREES,
    DOWN,
    IN,
    LEFT,
    ORIGIN,
    OUT,
    PI,
    RIGHT,
    TAU,
    UP,
    AddTextLetterByLetter,
    AnimationGroup,
    Arc,
    Circle,
    Create,
    FadeIn,
    FadeOut,
    Indicate,
    LaggedStart,
    Line,
    MovingCameraScene,
    Prism,
    Rectangle,
    Restore,
    Rotate,
    RoundedRectangle,
    Scene,
    SurroundingRectangle,
    Text,
    ThreeDScene,
    Transform,
    ValueTracker,
    VGroup,
    VMobject,
    always_redraw,
    config,
    smooth,
    there_and_back,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from autorelabel import banner

config.background_color = "#000000"

MONO = "JetBrains Mono"
FG = "#E6E6E6"
MUTED = "#8A8A8A"
GOLD = "#FFD15C"
SHADOW = "#{:02x}{:02x}{:02x}".format(*banner.SHADOW)


def hexrgb(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def mono(text: str, size: float = 28, color: str = FG, weight: str = "NORMAL") -> Text:
    return Text(text, font=MONO, font_size=size, color=color, weight=weight)


# ------------------------------------------------------------------ the banner, cell by cell
def _box_char(ch: str, cx: float, cy: float, w: float, h: float) -> VMobject:
    """The double-line box-drawing characters of the banner's shadow, as two polylines."""
    hw, hh, d = w / 2, h / 2, w * 0.17
    lines = {
        "═": [[(-hw, d), (hw, d)], [(-hw, -d), (hw, -d)]],
        "║": [[(-d, hh), (-d, -hh)], [(d, hh), (d, -hh)]],
        "╗": [[(-hw, d), (d, d), (d, -hh)], [(-hw, -d), (-d, -d), (-d, -hh)]],
        "╔": [[(hw, d), (-d, d), (-d, -hh)], [(hw, -d), (d, -d), (d, -hh)]],
        "╝": [[(-hw, -d), (d, -d), (d, hh)], [(-hw, d), (-d, d), (-d, hh)]],
        "╚": [[(hw, -d), (-d, -d), (-d, hh)], [(hw, d), (d, d), (d, hh)]],
    }[ch]
    group = VGroup()
    for line in lines:
        m = VMobject(stroke_color=SHADOW, stroke_width=2.2)
        m.set_points_as_corners([np.array([cx + x, cy + y, 0.0]) for x, y in line])
        group.add(m)
    return group


def banner_art(cell_w: float = 0.14, cell_h: float = 0.3) -> tuple[VGroup, VGroup]:
    """(blocks, shadow): one rectangle per "█" in the gradient, the shadow as line art."""
    lines = banner.big_lines()
    width = max(len(line) for line in lines)
    x0, y0 = -width * cell_w / 2, len(lines) * cell_h / 2
    blocks, shadow = VGroup(), VGroup()
    for r, row in enumerate(banner.color_cells(lines)):
        for c, (ch, rgb) in enumerate(row):
            cx, cy = x0 + (c + 0.5) * cell_w, y0 - (r + 0.5) * cell_h
            if ch == "█":
                # a hair wider than the cell, so neighbours join without seams
                blocks.add(Rectangle(width=cell_w * 1.06, height=cell_h * 1.04, stroke_width=0,
                                     fill_color=hexrgb(rgb), fill_opacity=1).move_to([cx, cy, 0]))
            elif ch != " ":
                shadow.add(_box_char(ch, cx, cy, cell_w, cell_h))
    return blocks, shadow


class Banner(Scene):
    def construct(self):
        blocks, shadow = banner_art()
        art = VGroup(blocks, shadow).move_to(UP * 0.9)
        rng = random.Random(7)
        for b in blocks:
            b.save_state()
            b.shift(np.array([rng.uniform(-6, 6), rng.uniform(-4, 4), 0]))
            b.scale(0.15).rotate(rng.uniform(-2, 2)).set_opacity(0)
        order = sorted(blocks, key=lambda m: m.saved_state.get_x() + rng.uniform(0, 0.6))
        self.play(LaggedStart(*[Restore(b) for b in order], lag_ratio=0.006, run_time=2.0))
        self.play(Create(shadow, lag_ratio=0.004), run_time=0.7)

        tag = mono(banner.TAGLINE, 30, FG, "BOLD").next_to(art, DOWN, buff=0.55)
        sub = mono("timed · auto-graded · real RHEL 10 VMs · graded after a reboot", 24, MUTED)
        sub.next_to(tag, DOWN, buff=0.3)
        self.play(AddTextLetterByLetter(tag, time_per_char=0.022))
        self.play(FadeIn(sub, shift=UP * 0.15), run_time=0.6)

        # a light sweep over the letters
        sweep = sorted(blocks, key=lambda m: m.get_x())
        self.play(LaggedStart(*[b.animate(rate_func=there_and_back).set_fill("#FFF4D6")
                                for b in sweep], lag_ratio=0.004, run_time=1.2))
        self.wait(0.5)
        self.play(FadeOut(VGroup(art, tag, sub), shift=UP * 0.3), run_time=0.6)


# ------------------------------------------------------------------ the lab, in 3D
# Manim's Cairo 3D camera has no depth buffer: it sorts 3D pieces by the depth of their centre and
# draws everything flat on top. So the floor is small tiles and the wires are short floor strips.
RED = "#CC0000"
ORANGE = "#FF6A2B"
GREY = "#6A6A6A"
WIRE = "#505050"


def tile(x: float, y: float, w: float, h: float, color: str, z: float = 0.0, stroke: str | None = None):
    sq = Rectangle(width=w, height=h, fill_color=color, fill_opacity=1, stroke_width=1 if stroke else 0,
                   stroke_color=stroke or color, shade_in_3d=True)
    return sq.move_to([x, y, z])


def floor(cols: int = 17, rows: int = 10, size: float = 0.5) -> VGroup:
    x0, y0 = -(cols - 1) * size / 2, -(rows - 1) * size / 2
    return VGroup(*[tile(x0 + c * size, y0 + r * size, size, size, "#101010", stroke="#1D1D1D")
                    for c in range(cols) for r in range(rows)])


def wire(*points, color: str = WIRE, dashed: bool = False, step: float = 0.25) -> VGroup:
    """A strip on the floor along the polyline, in short pieces (in order, for pulses)."""
    out = VGroup()
    for (x1, y1), (x2, y2) in pairwise(points):
        n = max(1, round(np.hypot(x2 - x1, y2 - y1) / step))
        for i in range(n):
            if dashed and i % 2:
                continue
            ax, ay = x1 + (x2 - x1) * i / n, y1 + (y2 - y1) * i / n
            bx, by = x1 + (x2 - x1) * (i + 1) / n, y1 + (y2 - y1) * (i + 1) / n
            horiz = abs(by - ay) < 1e-9
            w = abs(bx - ax) + 0.07 if horiz else 0.07
            h = 0.07 if horiz else abs(by - ay) + 0.07
            out.add(tile((ax + bx) / 2, (ay + by) / 2, w, h, color, z=0.01))
    return out


def node_box(color: str, x: float, y: float, height: float = 0.8) -> Prism:
    box = Prism(dimensions=[1.0, 1.0, height]).set_fill(color, opacity=1).set_stroke("#000000", width=1)
    return box.move_to([x, y, height / 2 + 0.02])


def note(name: str, text: str, color: str, width: int = 8) -> VGroup:
    return VGroup(mono(f"{name:<{width}}", 22, color, "BOLD"), mono(text, 22, FG)).arrange(RIGHT, buff=0.15)


class Lab(ThreeDScene):
    def fixed(self, *mobs):
        self.add_fixed_in_frame_mobjects(*mobs)
        self.remove(*mobs)

    def grow(self, boxes):
        for b in boxes:
            b.save_state()
            b.stretch(0.02, 2, about_edge=IN)
        return [Restore(b) for b in boxes]

    def labels(self, pairs):
        out = []
        for box, name, ip, color in pairs:
            g = VGroup(mono(name, 22, color, "BOLD"), mono(ip, 16, MUTED)).arrange(DOWN, buff=0.06)
            g.move_to(box.get_center() + OUT * (box.height / 2 + 0.6))
            out.append(g)
        self.add_fixed_orientation_mobjects(*out)
        self.remove(*out)
        return out

    def construct(self):
        self.set_camera_orientation(phi=60 * DEGREES, theta=-84 * DEGREES, zoom=0.8)
        ground = floor()
        title = mono("A real RHEL 10 lab on your Linux host", 34, FG, "BOLD")
        sub = mono("libvirt/KVM or VirtualBox · fully offline, like the exam", 22, MUTED)
        head = VGroup(title, sub).arrange(DOWN, buff=0.14).to_edge(UP, buff=0.35)
        self.fixed(head)
        self.move_camera(theta=-64 * DEGREES, added_anims=[FadeIn(ground, lag_ratio=0.002),
                                                            FadeIn(head, shift=DOWN * 0.15)], run_time=1.2)

        bus = wire((-3.6, 0), (3.6, 0))
        util, n1, n2 = node_box(GREY, -2.4, 1.4), node_box(RED, 0.4, 1.9), node_box(RED, 2.4, -1.4)
        util_w, n2_w = wire((-2.4, 0.9), (-2.4, 0)), wire((2.4, -0.9), (2.4, 0))
        n1_w = wire((0.4, 1.4), (0.4, 0), color=RED, dashed=True, step=0.15)
        cut = mono("✕", 34, RED, "BOLD").move_to([0.4, 0.7, 0.05])     # node1's link is down
        self.add_fixed_orientation_mobjects(cut)
        self.remove(cut)
        self.play(FadeIn(bus, lag_ratio=0.05), run_time=0.5)
        self.play(*self.grow([util, n1, n2]), FadeIn(util_w), FadeIn(n2_w), FadeIn(n1_w), run_time=0.9)
        labels = self.labels([(util, "utility", "172.25.250.10", FG), (n1, "node1", ".11", FG),
                              (n2, "node2", ".12", FG)])
        self.play(*[FadeIn(lab_) for lab_ in labels], FadeIn(cut, scale=1.5), run_time=0.4)

        notes = VGroup(
            note("utility", "the classroom server: repositories, DNS, NTP, NFS", GREY),
            note("node1", "no network yet: configure it from the console", RED),
            note("node2", "root password unknown: break into the boot", RED),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.14).to_edge(DOWN, buff=0.4)
        self.fixed(notes)
        self.play(LaggedStart(*[FadeIn(n, shift=UP * 0.15) for n in notes], lag_ratio=0.5), run_time=1.4)
        self.wait(1.0)

        # RHCE: a control node and managed nodes
        self.play(FadeOut(notes), FadeOut(n1), FadeOut(n2), FadeOut(n1_w), FadeOut(n2_w), FadeOut(cut),
                  *[FadeOut(lab_) for lab_ in labels[1:]], run_time=0.5)
        ctl = node_box(GOLD, 1.0, 1.4, 1.0)
        managed = [node_box(ORANGE, x, -1.4) for x in (-2.0, 0.4, 2.8)]
        wires = [wire((1.0, 0.9), (1.0, 0))] + [wire((m.get_x(), -0.9), (m.get_x(), 0)) for m in managed]
        rhce = VGroup(
            note("control", "you, as student: Ansible, ansible-navigator, VS Code in a browser", GOLD),
            note("node1-3", "managed nodes: configured only with Ansible", ORANGE),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.14).to_edge(DOWN, buff=0.4)
        self.fixed(rhce)
        self.play(*self.grow([ctl, *managed]), *[FadeIn(w) for w in wires], FadeIn(rhce, shift=UP * 0.15),
                  run_time=0.9)
        mlabels = self.labels([(ctl, "control", ".20", GOLD)] +
                              [(m, f"node{i}", f".2{i}", FG) for i, m in enumerate(managed, 1)])
        self.play(*[FadeIn(lab_) for lab_ in mlabels], run_time=0.4)
        # Ansible runs: pulses from control along the wires to every managed node
        pulses = [wire((1.0, 0.9), (1.0, 0), (m.get_x(), 0), (m.get_x(), -0.9), color=GOLD) for m in managed]
        for _ in range(2):
            self.play(*[LaggedStart(*[FadeIn(seg, rate_func=there_and_back) for seg in p], lag_ratio=0.25)
                        for p in pulses], run_time=0.8)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.6)


# ------------------------------------------------------------------ text on a terminal grid
class Grid:
    """Monospace text placed by (row, col) like a real terminal. Manim places text by its ink box,
    which shifts with descenders, so every string starts with an invisible full-height "│" that
    pins it to its cell."""

    def __init__(self, origin, size: int = 16):
        self.size = size
        self.adv = size / 120
        self.lh = Text("│", font=MONO, font_size=size).height
        self.origin = np.array([*origin, 0.0])

    def at(self, row: float, col: float) -> np.ndarray:
        """Top-left corner of a cell."""
        return self.origin + np.array([col * self.adv, -row * self.lh, 0.0])

    def put(self, row: int, col: int, text: str, color: str = FG, weight: str = "NORMAL",
            slant: str = "NORMAL") -> Text:
        t = Text("│" + text, font=MONO, font_size=self.size, color=color, weight=weight, slant=slant)
        bar = t[0]
        anchor = np.array([bar.get_center()[0], bar.get_top()[1], 0.0])
        t.shift(self.at(row, col - 1) + np.array([self.adv / 2, 0, 0]) - anchor)
        t.remove(bar)
        return t

    def rich(self, row: int, col: int, markup: str, color: str = FG, code: str = GOLD) -> VGroup:
        """**bold**, `code` and *italic* segments, in place."""
        out, pos = VGroup(), col
        for i, part in enumerate(re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)", markup)):
            if not part:
                continue
            if part.startswith("**"):
                text, kw = part[2:-2], {"weight": "BOLD"}
            elif part.startswith("`"):
                text, kw = part[1:-1], {"color": code}
            elif part.startswith("*") and i % 2:
                text, kw = part[1:-1], {"slant": "ITALIC"}
            else:
                text, kw = part, {}
            if text.strip():
                out.add(self.put(row, pos, text, **{"color": color, **kw}))
            pos += len(text)
        return out

    def box(self, row1: float, col1: float, row2: float, col2: float, fill: str, stroke: str | None = None,
            radius: float = 0.0) -> VMobject:
        a, b = self.at(row1, col1), self.at(row2, col2)
        cls = RoundedRectangle if radius else Rectangle
        kw = {"corner_radius": radius} if radius else {}
        r = cls(width=b[0] - a[0], height=a[1] - b[1], fill_color=fill, fill_opacity=1,
                stroke_color=stroke or fill, stroke_width=1.5 if stroke else 0, **kw)
        return r.move_to((a + b) / 2)


# ------------------------------------------------------------------ the exam screen
PANEL = "#1D1D1D"
WINDOW = "#111111"
EDGE = "#303030"
ACCENT = "#FFA62B"          # Textual's accent
OK = "#4EBF71"
WARN = "#FFA62B"
ERR = "#E0455E"
SELECT = "#1666B0"
BADGES = {"easy": OK, "medium": "#E8C547", "hard": "#E0455E"}

EXAM_TASKS = [  # bank sample rhcsa --seed 42
    ("Configure networking on node1", "medium"), ("Configure software repositories on node1 and node2", "easy"),
    ("Recover root access on node2", "hard"), ("Switch user and create a file as that user", "easy"),
    ("Add a Flatpak remote by URL and key", "medium"), ("Install a package group", "easy"),
    ("Process a file line by line", "medium"), ("Run a scheduled job with a lower priority", "medium"),
    ("Create LVM storage with a specific extent size", "hard"),
    ("Remove a physical volume from a volume group", "medium"), ("Automount network home directories", "hard"),
    ("Create and mount a VFAT file system", "medium"), ("Schedule a one-time job with at", "easy"),
    ("Schedule a job with a systemd timer", "medium"), ("Create users and a group", "easy"),
    ("Modify and remove user accounts", "easy"), ("Password aging policies", "medium"),
    ("Serve a web site on a non-standard port", "hard"), ("Let sshd listen on an additional port", "hard"),
    ("Key-only SSH login for one account", "hard"),
]
TASK1 = [
    "## Task 1: Configure networking on node1", "*15 points · medium · about 8 min · on node1 ·*",
    "*use the console*", "",
    "node1 has no network configuration on its lab interface,",
    "so you cannot reach it over SSH yet. Use its console",
    "(`./autorelabel console node1`) and configure:", "",
    "• IPv4 address: `172.25.250.11/24`", "• Default gateway: `172.25.250.1`",
    "• DNS server: `172.25.250.10`", "• Hostname: `node1.lab.example.com`", "",
    "The connection must come up automatically at boot.",
]
TASK18 = [
    "## Task 18: Serve a web site on a non-standard port", "*20 points · hard · about 12 min · on node2*", "",
    "Apache on node2 is configured to listen on TCP port",
    "**8909** and to serve the existing page in `/var/www/html`,",
    "but the service fails to start.", "", "Make it work:",
    "• the page must be reachable **from other systems** at",
    "  `http://node2.lab.example.com:8909/`",
    "• the web server must start automatically at boot",
    "• SELinux must remain enforcing; do not change the port",
    "  or the content",
]


def clock_text(seconds: float) -> str:
    s = int(max(0, seconds))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


class Exam(MovingCameraScene):
    LIST_W = 44

    def task_row(self, g: Grid, n: int, mark: str = "") -> VGroup:
        title, diff = EXAM_TASKS[n - 1]
        room = self.LIST_W - 6 - len(diff) - 3
        title = title if len(title) <= room else title[: room - 1] + "…"
        row = VGroup(g.put(n, 4, f"{n:2}. {title}"), g.put(n, self.LIST_W - len(diff), diff, BADGES[diff]))
        row[1].set_opacity(0.75)
        if mark:
            row.add(g.put(n, 1, "✔", OK, "BOLD"))
        return row

    def pane(self, g: Grid, lines: list[str]) -> VGroup:
        out = VGroup()
        for i, line in enumerate(lines, start=1):
            if line.startswith("## "):
                out.add(g.put(i, self.LIST_W + 3, line[3:], ACCENT, "BOLD"))
            elif line:
                italic = line.startswith("*") and not line.startswith("**")
                out.add(g.rich(i, self.LIST_W + 3, line, MUTED if italic else FG))
        return out

    def construct(self):
        frame = self.camera.frame
        g = Grid((-50 * 16 / 120, 11 * Text("│", font=MONO, font_size=16).height), 16)
        window = g.box(0, 0, 22, 100, WINDOW, EDGE, radius=0.08)
        header = g.box(0, 0, 1, 100, PANEL)
        nodebar = g.box(21, 0, 22, 100, PANEL)
        sep = Line(g.at(1, self.LIST_W + 1.5), g.at(21, self.LIST_W + 1.5), stroke_color=EDGE, stroke_width=2)
        done = {1, 2, 4}
        title = g.put(0, 2, "RHCSA EXAM · 20 tasks · 3 marked done", FG, "BOLD")
        rows = {n: self.task_row(g, n, "✔" if n in done else "") for n in range(1, 21)}
        select = g.box(1, 0.3, 2, self.LIST_W + 1, SELECT)
        pane1 = self.pane(g, TASK1)
        nodes = VGroup(g.put(21, 2, "Nodes:", FG, "BOLD"), g.box(21, 9, 22, 16, FG), g.put(21, 9, "▸node1", WINDOW),
                       g.put(21, 17, "● running", OK), g.put(21, 30, "node2", FG), g.put(21, 36, "● running", OK),
                       g.put(21, 50, "←/→ select · n actions · d done · x submit", MUTED))

        rem = ValueTracker(2 * 3600 + 41 * 60 + 7)
        rem.add_updater(lambda m, dt: m.increment_value(-dt))

        def clock():
            v = rem.get_value()
            color = ERR if v <= 120 else WARN if v <= 600 else FG
            t = g.put(0, 89, "⏱ " + clock_text(v), "#111111" if v <= 120 else color, "BOLD")
            if v <= 120:
                return VGroup(g.box(0, 88.3, 1, 99.7, ERR), t)
            return t

        clk = always_redraw(clock)
        self.add(rem)
        self.play(FadeIn(VGroup(window, header, nodebar, sep)), run_time=0.4)
        self.play(FadeIn(select), FadeIn(title), FadeIn(clk), FadeIn(nodes),
                  LaggedStart(*[FadeIn(rows[n], shift=RIGHT * 0.1) for n in rows], lag_ratio=0.06),
                  FadeIn(pane1), run_time=1.1)
        self.wait(0.3)

        # down the list to task 18
        self.play(select.animate.move_to(g.box(18, 0.3, 19, self.LIST_W + 1, SELECT)), FadeOut(pane1),
                  run_time=0.9, rate_func=smooth)
        pane18 = self.pane(g, TASK18)
        self.play(FadeIn(pane18, lag_ratio=0.03), run_time=0.6)
        self.play(frame.animate.set(width=8.2).move_to(g.at(6.5, 73)), run_time=0.55)
        self.wait(1.3)

        # a second terminal: the work
        t = Grid((-1.2, -0.75), 16)
        term = VGroup(t.box(-1, 0, 7.4, 62, "#0A0A0A", "#3A3A3A", radius=0.08), t.box(-1, 0, 0, 62, "#1A1A1A"),
                      t.put(-1, 25, "root@node2: ~", MUTED))
        dots = VGroup(*[Circle(radius=0.055, fill_color=c, fill_opacity=1, stroke_width=0)
                        .move_to(t.at(-0.5, 1.2 + i * 1.1)) for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"])])
        term.add(dots)
        self.play(FadeIn(term, shift=UP * 0.4), frame.animate.set(width=9.6).move_to(t.at(3.2, 31)), run_time=0.6)
        prompt = "[root@node2 ~]# "
        cmds = ["semanage port -a -t http_port_t -p tcp 8909", "systemctl enable --now httpd",
                "firewall-cmd --add-port=8909/tcp"]
        row, typed = 0.5, VGroup()
        for cmd in cmds:
            p = t.put(row, 1, prompt, "#9A9A9A")
            c = t.put(row, 1 + len(prompt), cmd, "#F4F4F4")
            typed.add(p, c)
            self.add(p)
            self.play(AddTextLetterByLetter(c, time_per_char=0.019), run_time=len(cmd) * 0.019)
            self.wait(0.1)
            row += 1
            if cmd.startswith("firewall-cmd"):
                typed.add(t.put(row, 1, "success", FG))
                self.add(typed[-1])
                row += 1
        typed.add(t.put(row, 1, prompt, "#9A9A9A"), t.box(row, 1 + len(prompt), row + 1, 2 + len(prompt), "#F4F4F4"))
        self.add(*typed[-2:])
        self.wait(0.4)

        # mark it done, then fast-forward the clock
        new_title = g.put(0, 2, "RHCSA EXAM · 20 tasks · 4 marked done", FG, "BOLD")
        self.play(FadeOut(term), FadeOut(typed), frame.animate.set(width=config.frame_width).move_to(ORIGIN),
                  run_time=0.5)
        self.play(FadeIn(g.put(18, 1, "✔", OK, "BOLD"), scale=1.6), FadeOut(title), FadeIn(new_title), run_time=0.4)
        self.play(frame.animate.set(width=6.4).move_to(g.at(3.2, 83)), run_time=0.5)
        rem.clear_updaters()
        ff = g.put(0, 80, "▶▶ ×2000", MUTED, "BOLD")
        self.play(FadeIn(ff), run_time=0.2)
        self.play(rem.animate.set_value(0), run_time=1.9, rate_func=lambda x: smooth(x) * 0.9 + x * 0.1)
        self.remove(rem)
        shade = Rectangle(width=30, height=20, fill_color="#000000", fill_opacity=0.72, stroke_width=0)
        msg = VGroup(mono("⏱ Time is up", 40, ERR, "BOLD"), mono("the lab is frozen and graded", 28, FG))
        msg.arrange(DOWN, buff=0.22)
        card = SurroundingRectangle(msg, buff=0.45, color=ERR, stroke_width=3, fill_color="#140608",
                                    fill_opacity=1, corner_radius=0.12)
        self.play(FadeOut(ff), frame.animate.set(width=config.frame_width).move_to(ORIGIN), FadeIn(shade),
                  FadeIn(VGroup(card, msg), scale=0.9), run_time=0.55)
        self.wait(0.8)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.6)


# ------------------------------------------------------------------ grading after a reboot
class Grading(Scene):
    def construct(self):
        title = mono("Every node reboots before grading", 36, FG, "BOLD")
        sub = mono("only what survives the reboot counts", 24, MUTED)
        head = VGroup(title, sub).arrange(DOWN, buff=0.16).to_edge(UP, buff=0.45)
        cards, states = VGroup(), []
        for name in ("utility", "node1", "node2"):
            box = RoundedRectangle(width=3.3, height=1.3, corner_radius=0.12, fill_color=PANEL, fill_opacity=1,
                                   stroke_color=EDGE, stroke_width=2)
            st = mono("● running", 22, OK).move_to(box.get_center() + DOWN * 0.28)
            cards.add(VGroup(box, mono(name, 28, FG, "BOLD").move_to(box.get_center() + UP * 0.26), st))
            states.append(st)
        cards.arrange(RIGHT, buff=0.45).move_to(UP * 1.2)
        self.play(FadeIn(head, shift=DOWN * 0.15),
                  LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in cards], lag_ratio=0.15), run_time=0.8)

        reboot = [mono("rebooting", 22, WARN).move_to(s).shift(LEFT * 0.15) for s in states]
        spin = [Arc(radius=0.12, angle=PI * 1.4, color=WARN, stroke_width=4).next_to(r, RIGHT, buff=0.18)
                for r in reboot]
        self.play(*[Transform(s, r) for s, r in zip(states, reboot, strict=True)], *[FadeIn(a) for a in spin],
                  run_time=0.3)
        self.play(*[Rotate(a, -TAU * 1.6, about_point=a.get_arc_center()) for a in spin], run_time=1.1,
                  rate_func=lambda x: x)
        ups = [mono("● up", 22, OK).move_to(s) for s in states]
        back_up = [AnimationGroup(Transform(s, u), FadeOut(a)) for s, u, a in zip(states, ups, spin, strict=True)]
        self.play(LaggedStart(*back_up, lag_ratio=0.3), run_time=0.7)

        panel = RoundedRectangle(width=12.6, height=2.75, corner_radius=0.12, fill_color="#0D0D0D", fill_opacity=1,
                                 stroke_color=EDGE, stroke_width=2).move_to(DOWN * 1.35)
        g = Grid((panel.get_left()[0] + 0.3, panel.get_top()[1] - 0.22), 21)
        task = VGroup(g.put(0, 0, "Task 18: Serve a web site on a non-standard port", ACCENT, "BOLD"),
                      g.put(0, 59, "13.33/20", WARN, "BOLD"))
        checks = [
            VGroup(g.put(1.3, 0, "✔", OK, "BOLD"), g.put(1.3, 2, "httpd is enabled and running")),
            VGroup(g.put(2.3, 0, "✔", OK, "BOLD"),
                   g.put(2.3, 2, "tcp/8909 is http_port_t (local policy) and SELinux is enforcing")),
            VGroup(g.put(3.3, 0, "✘", ERR, "BOLD"),
                   g.put(3.3, 2, "the utility server gets the page from 172.25.250.12:8909")),
        ]
        why = g.put(4.3, 2, "worked before the reboot, not after: not persistent", WARN, "BOLD")
        self.play(FadeIn(panel), FadeIn(task[0]), run_time=0.4)
        self.play(LaggedStart(*[FadeIn(c, shift=RIGHT * 0.15) for c in checks], lag_ratio=0.45), run_time=1.2)
        self.play(FadeIn(why, shift=RIGHT * 0.15), FadeIn(task[1]), run_time=0.4)
        fix = VGroup(mono("the fix:", 22, MUTED), mono("firewall-cmd --permanent --add-port=8909/tcp", 22, GOLD))
        fix.arrange(RIGHT, buff=0.25).next_to(panel, DOWN, buff=0.3)
        self.play(FadeIn(fix, shift=UP * 0.1), Indicate(why, color=WARN, scale_factor=1.04), run_time=0.7)
        self.wait(1.0)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)


# ------------------------------------------------------------------ results
class Results(Scene):
    def construct(self):
        score = ValueTracker(0)
        total, mark, final = 300, 210, 258

        def number():
            v = score.get_value()
            n = mono(f"{v:.0f}", 110, OK if v >= mark else FG, "BOLD")
            return VGroup(n, mono("/ 300", 44, MUTED)).arrange(RIGHT, buff=0.3, aligned_edge=DOWN).move_to(UP * 2.05)

        num = always_redraw(number)
        x0, width = -5.5, 11.0
        track = Rectangle(width=width, height=0.3, fill_color="#222222", fill_opacity=1, stroke_width=0)
        track.move_to(UP * 0.55)

        def fill():
            v = max(score.get_value(), 0.001)
            r = Rectangle(width=width * v / total, height=0.3, fill_color=OK if v >= mark else "#9A9A9A",
                          fill_opacity=1, stroke_width=0)
            return r.align_to(track, LEFT).set_y(track.get_y())

        bar = always_redraw(fill)
        tick_x = x0 + width * mark / total
        tick = Line([tick_x, 0.25, 0], [tick_x, 0.85, 0], stroke_color=FG, stroke_width=3)
        tick_label = mono("pass mark 210", 18, MUTED).next_to(tick, DOWN, buff=0.12)
        self.add(score)
        self.play(FadeIn(track), FadeIn(tick), FadeIn(tick_label), FadeIn(num), FadeIn(bar), run_time=0.4)
        self.play(score.animate.set_value(final), run_time=1.8, rate_func=smooth)
        stamp = mono("PASS", 46, "#0D0D0D", "BOLD")
        badge = VGroup(SurroundingRectangle(stamp, buff=0.18, color=OK, fill_color=OK, fill_opacity=1,
                                            corner_radius=0.1), stamp).next_to(num, RIGHT, buff=0.6)
        self.play(FadeIn(badge, scale=1.6), run_time=0.35)

        rows = VGroup()
        g = Grid((-4.2, -0.95), 24)
        g.origin[1] += g.lh / 2                       # row 0 is centred on y = -0.95
        for i, (name, got, possible) in enumerate((("easy", 60, 60), ("medium", 105, 120), ("hard", 93.3, 120))):
            row = i * 0.52 / g.lh
            y = g.at(row + 0.5, 0)[1]
            label = g.put(row, 0, name, BADGES[name], "BOLD")
            back = Rectangle(width=5.4, height=0.22, fill_color="#222222", fill_opacity=1, stroke_width=0)
            back.move_to([-2.3, y, 0], aligned_edge=LEFT)
            front = Rectangle(width=5.4 * got / possible, height=0.22, fill_color=BADGES[name], fill_opacity=1,
                              stroke_width=0).move_to([-2.3, y, 0], aligned_edge=LEFT).set_z_index(1)
            value = g.put(row, (3.45 + 4.2) / g.adv, f"{got:g}/{possible}", FG)
            rows.add(VGroup(label, back, value, front))
        for row in rows:
            row[3].save_state()
            row[3].stretch(0.001, 0, about_edge=LEFT)
        self.play(LaggedStart(*[AnimationGroup(FadeIn(r[:3]), Restore(r[3])) for r in rows], lag_ratio=0.25),
                  run_time=1.0)
        more = mono("by task and domain · every check explained · solutions · docs · retake", 21, MUTED)
        more.to_edge(DOWN, buff=0.45)
        self.play(FadeIn(more, shift=UP * 0.1), run_time=0.4)
        self.wait(1.0)
        self.remove(score)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)


# ------------------------------------------------------------------ the signature move
class Finale(Scene):
    def construct(self):
        g = Grid((-5.6, 2.75), 26)
        steps = [("switch_root:/# ", "mount -o remount,rw /sysroot", []),
                 ("switch_root:/# ", "chroot /sysroot", []),
                 ("sh-5.2# ", "passwd root", ["New password:", "Retype new password:",
                                              "passwd: all authentication tokens updated successfully."]),
                 ("sh-5.2# ", "touch /.autorelabel", [])]
        row, shown, last = 0, VGroup(), None
        for prompt, cmd, output in steps:
            final = cmd.startswith("touch")
            p = g.put(row, 0, prompt, "#9A9A9A")
            c = g.put(row, len(prompt), cmd, GOLD if final else "#F4F4F4", "BOLD" if final else "NORMAL")
            self.add(p)
            self.play(AddTextLetterByLetter(c, time_per_char=0.04 if final else 0.022),
                      run_time=len(cmd) * (0.04 if final else 0.022))
            shown.add(p, c)
            row += 1
            for line in output:
                shown.add(g.put(row, 0, line, MUTED))
                row += 1
            if output:
                self.add(*shown[-len(output):])
                self.wait(0.2)
            last = c
        glow = SurroundingRectangle(last, buff=0.1, color=GOLD, stroke_width=3, corner_radius=0.08)
        self.play(Create(glow), run_time=0.5)
        line1 = mono("Forget it after rd.break and your node won't let you log in.", 24, FG)
        line2 = mono("You'll never forget again.", 30, GOLD, "BOLD")
        words = VGroup(line1, line2).arrange(DOWN, buff=0.25).to_edge(DOWN, buff=0.9)
        self.play(FadeIn(line1, shift=UP * 0.1), run_time=0.5)
        self.play(FadeIn(line2, shift=UP * 0.1), run_time=0.5)
        self.wait(0.8)
        self.play(FadeOut(VGroup(shown, glow, words)), run_time=0.5)

        blocks, shadow = banner_art(0.09, 0.19)
        art = VGroup(blocks, shadow).move_to(UP * 0.7)
        cmd = mono("./autorelabel", 34, FG, "BOLD")
        cmd_box = SurroundingRectangle(cmd, buff=0.2, color=EDGE, fill_color=PANEL, fill_opacity=1,
                                       corner_radius=0.1)
        url = mono("github.com/syed-913/autorelabel-rhcsa-rhce", 22, MUTED)
        end = VGroup(VGroup(cmd_box, cmd), url).arrange(DOWN, buff=0.35).next_to(art, DOWN, buff=0.6)
        self.play(FadeIn(art, scale=0.96), run_time=0.6)
        self.play(FadeIn(end, shift=UP * 0.1), run_time=0.5)
        self.wait(1.5)
        self.play(FadeOut(VGroup(art, end)), run_time=0.6)
