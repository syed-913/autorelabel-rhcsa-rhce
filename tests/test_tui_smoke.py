"""Headless smoke tests: every main screen mounts and renders without errors."""

from __future__ import annotations

import asyncio

import pytest

from autorelabel import config, paths
from autorelabel.tui.app import AutorelabelApp
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
