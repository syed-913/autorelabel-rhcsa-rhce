"""Headless smoke tests: every main screen mounts and renders without errors."""

from __future__ import annotations

import ast
import asyncio
import re
from pathlib import Path

import pytest

from autorelabel import config, paths
from autorelabel.tui.app import WELCOME, AutorelabelApp
from autorelabel.tui.screens import HistoryScreen, HomeScreen, SettingsScreen


@pytest.fixture()
def configured(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(paths, "HISTORY_FILE", tmp_path / "history.jsonl")
    monkeypatch.setattr(paths, "SESSIONS", tmp_path / "sessions")
    monkeypatch.setenv("VBOX_USER_HOME", "")          # config.save sets it; restored after the test
    st = config.Settings(provider="libvirt", storage_dir=str(tmp_path), iso_path=str(tmp_path / "x.iso"))
    (tmp_path / "x.iso").write_bytes(b"0")
    config.save(st)
    monkeypatch.setattr("autorelabel.box.box_status", lambda *_a, **_k: (True, "test box"))
    return st


def test_home_settings_history_render(configured):
    async def run() -> None:
        app = AutorelabelApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)
            app.push_screen(SettingsScreen())
            await pilot.pause()
            await pilot.press("escape")
            app.push_screen(HistoryScreen())
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert isinstance(app.screen, HomeScreen)

    asyncio.run(run())


@pytest.mark.parametrize("exam", ["rhcsa", "rhce"])
def test_practice_picker_lists_the_bank(configured, exam):
    from textual.widgets import SelectionList

    from autorelabel.bank import load_bank
    from autorelabel.tui.exam import PracticePicker

    async def run() -> None:
        app = AutorelabelApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause()
            app.push_screen(PracticePicker(exam))
            await pilot.pause()
            options = app.screen.query_one(SelectionList).option_count
            assert options == len(load_bank(exam).tasks)

    asyncio.run(run())


def test_banner_fits_and_degrades():
    from autorelabel import banner

    big = banner.big_lines()
    assert len(big) == 6 and max(len(x) for x in big) <= 92
    assert "\x1b[" in banner.render_ansi(width=120, color=True)
    assert "\x1b[" not in banner.render_ansi(width=60, color=False)


def test_fit_shortens_with_an_ellipsis():
    from autorelabel.tui.exam import fit

    assert fit("Install a package group", 30) == "Install a package group"
    assert fit("Configure software repositories on node1 and node2", 20) == "Configure software …"
    assert len(fit("x" * 50, 20)) == 20


def test_progress_counters_drive_a_bar_not_the_log(configured):
    from textual.widgets import RichLog

    from autorelabel import proc
    from autorelabel.tui.common import OperationScreen

    def fn(step, line, cancel):
        step("Starting the utility server")
        line("Uploading base box image as volume into Libvirt storage...")
        for pct in range(0, 101, 5):
            line(proc.Progress(f"Progress: {pct}%"))
        cancel.wait(5)                  # still running: the bar is on screen

    async def run() -> None:
        app = AutorelabelApp()
        async with app.run_test(size=(120, 30)) as pilot:
            screen = OperationScreen("Preparing", fn)
            app.push_screen(screen)
            await pilot.pause(0.5)
            assert screen.query_one("#op-progress").display
            assert screen.query_one("#op-bar").percentage == 1.0
            log = screen.query_one("#op-log", RichLog)
            assert len(log.lines) == 2                  # the step and the upload line, no counters
            screen._log_line("==> utility: Creating image")
            await pilot.pause()
            assert not screen.query_one("#op-progress").display
            assert [s.text for s in log.lines][-2:] == ["Progress: 100%", "==> utility: Creating image"]
            screen.cancel.set()

    asyncio.run(run())


def test_storage_defaults_to_the_xdg_data_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    assert config.default_storage_dir() == tmp_path                 # no ~/.local/share: home
    (tmp_path / ".local" / "share").mkdir(parents=True)
    assert config.default_storage_dir() == tmp_path / ".local" / "share"
    monkeypatch.setenv("XDG_DATA_HOME", "relative/ignored")         # the spec: only absolute paths count
    assert config.default_storage_dir() == tmp_path / ".local" / "share"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert config.default_storage_dir() == tmp_path


# A newline inside a sentence. Textual wraps dialog text to the dialog's width, so a break typed for
# an 80-column terminal breaks the line a second time ("...then the RHEL 10 box" / "is" / "built once").
MID_SENTENCE = re.compile(r"[a-z0-9,;)]\n[A-Za-z(]")


def test_dialog_text_has_no_breaks_inside_sentences():
    from autorelabel import report

    found = []
    for path in sorted((Path(__file__).parents[1] / "src" / "autorelabel" / "tui").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) in ("Message", "Confirm"):
                found += [f"{path.name}:{c.lineno}" for c in ast.walk(node)
                          if isinstance(c, ast.Constant) and isinstance(c.value, str) and MID_SENTENCE.search(c.value)]
    assert not found
    for has_hint in (False, True):
        assert not MID_SENTENCE.search(report.notice(Path("report.txt"), has_hint))


def test_welcome_wraps_evenly_in_an_80x24_terminal(configured):
    from textual.geometry import Region
    from textual.widgets import Static

    from autorelabel.tui.common import Message

    async def run() -> None:
        app = AutorelabelApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app.push_screen(Message("Welcome to autorelabel", WELCOME))
            await pilot.pause()
            body = next(w for w in app.screen.query(Static) if type(w) is Static)   # not the title Label
            width, height = body.content_region.size
            lines = [s.text.rstrip() for s in body.render_lines(Region(0, 0, width, height))]
            lines = [line for line in lines if line]
            assert " ".join(lines).split() == WELCOME.split()
            assert all(len(line) > width * 0.75 for line in lines[:-1])     # no stray 1-3 word lines

    asyncio.run(run())


def test_doctor_offers_to_run_tested_fixes(configured, monkeypatch):
    from textual.widgets import Button

    from autorelabel import doctor
    from autorelabel.tui.common import Confirm
    from autorelabel.tui.screens import DoctorScreen

    broken = [doctor.Check("packer", "Packer", doctor.Status.FAIL, "not installed",
                           fix=["sudo apt install -y packer"], fixable=True)]
    monkeypatch.setattr("autorelabel.guides.family", lambda *_a: "debian")

    async def run(checks: list[doctor.Check], fixable: bool) -> None:
        monkeypatch.setattr(doctor, "run", lambda *_a, **_k: checks)
        app = AutorelabelApp()
        async with app.run_test(size=(100, 30)) as pilot:
            app.push_screen(DoctorScreen())
            await pilot.pause(0.3)
            assert app.screen.query_one("#fix", Button).disabled is not fixable
            await pilot.press("f")
            await pilot.pause()
            assert isinstance(app.screen, Confirm) is fixable

    asyncio.run(run(broken, True))
    asyncio.run(run([doctor.Check("packer", "Packer", doctor.Status.OK)], False))
