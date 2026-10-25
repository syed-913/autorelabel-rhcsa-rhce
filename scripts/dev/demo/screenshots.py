"""Screenshots of the real TUI for the README: the home, exam and results screens.

The app runs headless (Textual's test driver) in a throwaway workspace, so nothing touches your
setup or a lab. Only what needs running VMs is stubbed: the box status and the VM power states.
The exam is the bank's seed-42 RHCSA exam; the results come from the grader's own scoring,
fed a sample outcome (all checks pass except task 14, task 20 and the firewall check of task 18,
which worked before the reboot only).

    .venv/bin/python scripts/dev/demo/screenshots.py [output dir]     default: docs/media

Writes home.png, exam.png and results.png (rendered with headless Chrome or Chromium).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = Path(tempfile.mkdtemp(prefix="autorelabel-screenshots-"))
os.environ["AUTORELABEL_WORKSPACE"] = str(WORKSPACE)     # before autorelabel is imported
sys.path.insert(0, str(ROOT / "src"))

from autorelabel import box, config  # noqa: E402
from autorelabel import session as S  # noqa: E402
from autorelabel.bank import render  # noqa: E402
from autorelabel.engine import Engine  # noqa: E402
from autorelabel.fsutil import atomic_write_json  # noqa: E402
from autorelabel.grader import Grader  # noqa: E402
from autorelabel.tui import exam as exam_ui  # noqa: E402
from autorelabel.tui.app import AutorelabelApp  # noqa: E402

SEED = 42
SIZE = (120, 34)
FAILED_TASKS = {14, 20}                 # nothing on these survived (or was done)
NOT_PERSISTENT = {(18, "remote")}       # firewall rule added without --permanent
FONT = "JetBrains Mono"


def setup() -> tuple[S.Session, S.Session]:
    config.save(config.Settings(provider="libvirt", storage_dir="/srv/labs",
                                iso_path="/srv/labs/rhel-10.0-x86_64-dvd.iso", show_difficulty_during_exam=True))
    eng = Engine()

    # an exam 18:53 in, three tasks marked done
    running = eng.create("rhcsa", seed=SEED)
    running.state, running.started = S.IN_PROGRESS, time.time() - 1133
    running.marks = {"1": "done", "2": "done", "4": "done"}
    running.save()
    atomic_write_json(running.heartbeat_file, {"elapsed": 1133.0, "wall": time.time(), "boot_id": S.boot_id()})

    # the same exam, graded
    graded = eng.create("rhcsa", seed=SEED)
    graded.state, graded.started, graded.ended = S.GRADED, time.time() - 9000, time.time()
    graded.save()
    lab, bank = eng.lab("rhcsa"), eng.bank("rhcsa")
    grader = Grader(graded, lab, bank)
    cp: dict = {"pre": {}, "post": {}}
    for entry in graded.tasks:
        number, task = entry["number"], bank.tasks[entry["task"]]
        ctx = {**entry["params"], "lab": grader.facts}
        for chk, node in grader._expanded(task):
            failed = number in FAILED_TASKS and not chk.guard
            base = {"id": chk.id, "desc": render.render(chk.desc, ctx), "node": node, "weight": chk.weight,
                    "covers": list(chk.covers), "detail": "", "guard": chk.guard}
            lost = (number, chk.id) in NOT_PERSISTENT
            cp["pre"][f"{number}:{chk.id}"] = {**base, "status": "fail" if failed else "pass"}
            cp["post"][f"{number}:{chk.id}"] = {**base, "status": "fail" if failed or lost else "pass"}
    atomic_write_json(graded.results_file, grader.score(cp))
    S.set_current(graded)
    return running, graded


def stub() -> None:
    box.box_status = lambda settings, provider: (True, "RHEL 10.0 · built 2026-10-25")

    def nodes(self):                    # every VM is up
        self._show_nodes({n: "running" for n in self.node_names}, {})

    exam_ui.ExamScreen.refresh_nodes = nodes


async def shoot(running: S.Session, graded: S.Session, out: Path) -> list[Path]:
    shots = []
    app = AutorelabelApp()
    async with app.run_test(size=SIZE) as pilot:
        async def save(name: str) -> None:
            await pilot.pause(0.6)
            path = out / f"{name}.svg"
            path.write_text(app.export_screenshot(), encoding="utf-8")
            shots.append(path)

        await save("home")
        app.push_screen(exam_ui.ExamScreen(running))
        await pilot.pause(0.3)
        await pilot.press(*["down"] * 17)           # task 18
        await save("exam")
        app.pop_screen()
        app.push_screen(exam_ui.ResultsScreen(graded))
        await pilot.pause(0.3)
        await pilot.press(*["down"] * 17)
        await save("results")
    return shots


def to_png(svg: Path) -> Path:
    """Render with headless Chrome, in a local monospace font (the SVG names a web font)."""
    chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
    if not chrome:
        raise SystemExit("needs google-chrome or chromium to turn the SVG screenshots into PNG")
    text = svg.read_text(encoding="utf-8").replace("Fira Code", FONT)
    width = int(float(text.split('viewBox="0 0 ', 1)[1].split()[0]))
    height = int(float(text.split('viewBox="0 0 ', 1)[1].split()[1].rstrip('"')))
    page = svg.with_suffix(".html")
    page.write_text(f'<html><body style="margin:0;background:#000">{text}</body></html>', encoding="utf-8")
    png = svg.with_suffix(".png")
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
                        "--force-device-scale-factor=2", f"--window-size={width},{height}",
                        f"--screenshot={png}", page.as_uri()], check=True, capture_output=True)
    page.unlink()
    return png


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs" / "media").resolve()
    out.mkdir(parents=True, exist_ok=True)
    try:
        running, graded = setup()
        stub()
        for svg in asyncio.run(shoot(running, graded, out)):
            print(to_png(svg))
            svg.unlink()
    finally:
        shutil.rmtree(WORKSPACE, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
