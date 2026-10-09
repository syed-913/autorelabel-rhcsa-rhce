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
