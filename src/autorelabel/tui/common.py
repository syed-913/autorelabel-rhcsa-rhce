"""Shared TUI pieces: banner, confirm dialog, and the long-operation screen."""

from __future__ import annotations

import re
import threading
import traceback
from collections.abc import Callable
from typing import Any

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Label, ProgressBar, RichLog, Static

from .. import banner, log, proc, report

_log = log.get("tui")
_PERCENT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?%")


class Banner(Static):
    """The big gradient banner (falls back to the compact one on narrow terminals)."""

    def on_mount(self) -> None:
        self.refresh_banner()

    def on_resize(self) -> None:
        self.refresh_banner()

    def refresh_banner(self) -> None:
        width = self.app.size.width if self.app else 100
        self.update(banner.render_rich(width))


class Tagline(Static):
    def on_mount(self) -> None:
        t = Text(justify="center")
        t.append(banner.TAGLINE, style="bold")
        t.append("   ·   ")
        t.append(banner.MOTTO, style="dim italic")
        self.update(t)


class Confirm(ModalScreen[bool]):
    """Yes/No dialog. Dismisses with True on confirm."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, title: str, body: str, yes: str = "Continue", no: str = "Cancel", danger: bool = False):
        super().__init__()
        self._title, self._body, self._yes, self._no, self._danger = title, body, yes, no, danger

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, classes="title")
            yield Static(self._body)
            with Horizontal(id="dialog-buttons"):
                yield Button(self._yes, id="yes", variant="error" if self._danger else "primary")
                yield Button(self._no, id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_cancel(self) -> None:
        self.dismiss(False)


class Message(ModalScreen[None]):
    BINDINGS = [("escape", "close", "Close"), ("enter", "close", "Close")]

    def __init__(self, title: str, body: str):
        super().__init__()
        self._title, self._body = title, body

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title, classes="title")
            yield Static(self._body)
            with Horizontal(id="dialog-buttons"):
                yield Button("OK", id="ok", variant="primary")

    def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)


def copy_report(app, path) -> None:
    """Put a problem report on the clipboard (OSC 52: most terminals support it)."""
    try:
        app.copy_to_clipboard(path.read_text(encoding="utf-8"))
    except OSError:
        app.notify(f"Could not read {path}", severity="error")
        return
    app.notify("Problem report copied. If pasting doesn't work in your terminal, open the file: "
               f"{report.display_path(path)}", timeout=12)


OpFn = Callable[[Callable[[str], None], Callable[[str], None], threading.Event], Any]


class OperationScreen(Screen[Any]):
    """Runs a long operation in a worker thread with a step label, a live log and Cancel.
    Progress counters in the output (proc.Progress) drive a bar instead of filling the log.

    `fn(step, line, cancel)` does the work. On success the screen dismisses with the result.
    On failure it shows the error (with hint and log path) and offers Retry / Back; unless the
    error is the user's to fix, it also writes a problem report and offers to copy it.
    """

    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, title: str, fn: OpFn, *, cancellable: bool = True, show_log: bool = True):
        super().__init__()
        self.op_title = title
        self.fn = fn
        self.cancellable = cancellable
        self.show_log = show_log
        self.cancel = threading.Event()
        self.running = False
        self.report_path = None
        self.progress = ""          # the progress counter on show, "" if none

    def compose(self) -> ComposeResult:
        yield Static(self.op_title, id="op-title")
        yield Static("Starting…", id="op-step")
        with Horizontal(id="op-progress"):
            yield Static(id="op-progress-text")
            yield ProgressBar(id="op-bar", total=100, show_eta=False, show_percentage=False)
        yield RichLog(id="op-log", wrap=True, markup=False, max_lines=2000)
        with Horizontal(id="op-buttons"):
            yield Button("Cancel", id="cancel", variant="warning", disabled=not self.cancellable)
            yield Button("Retry", id="retry", variant="primary", classes="hidden")
            yield Button("Copy problem report", id="copy-report")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#retry").display = False
        self.query_one("#back").display = False
        self.query_one("#copy-report").display = False
        self.query_one("#op-progress").display = False
        if not self.show_log:
            self.query_one("#op-log").display = False
        self.start()

    def start(self) -> None:
        self.cancel.clear()
        self.running = True
        self.query_one("#retry").display = False
        self.query_one("#back").display = False
        self.query_one("#cancel").display = self.cancellable
        self.run_op()

    @work(thread=True, exclusive=True)
    def run_op(self) -> None:
        def step(s: str) -> None:
            self.app.call_from_thread(self._set_step, s)

        def line(s: str) -> None:
            self.app.call_from_thread(self._log_line, s)

        try:
            result = self.fn(step, line, self.cancel)
        except Exception as exc:  # shown to the user, with hint and log path when available
            _log.error("operation %r failed: %s\n%s", self.op_title, exc, traceback.format_exc())
            hint = getattr(exc, "hint", "")
            log_file = getattr(exc, "log_file", None)
            path = None
            if report.reportable(exc) and not self.cancel.is_set():
                path = report.write(self.op_title, report.describe(exc), hint=hint, log_file=log_file, exc=exc)
            self.app.call_from_thread(self._failed, report.describe(exc), hint, str(log_file) if log_file else "",
                                      path)
            return
        self.app.call_from_thread(self._done, result)

    def _set_step(self, s: str) -> None:
        self._end_progress()
        self.query_one("#op-step", Static).update(f"▶ {s}")
        self.query_one("#op-log", RichLog).write(Text(f"==> {s}", style="bold cyan"))

    def _log_line(self, s: str) -> None:
        if isinstance(s, proc.Progress):
            self._show_progress(s.strip())
            return
        self._end_progress(s)
        self.query_one("#op-log", RichLog).write(Text(s))

    def _show_progress(self, s: str) -> None:
        pct = _PERCENT.search(s)
        bar = self.query_one("#op-bar", ProgressBar)
        if pct:
            bar.update(total=100, progress=min(float(pct.group(1)), 100.0))
        else:
            bar.update(total=None)          # no percentage: an indeterminate bar
        self.query_one("#op-progress-text", Static).update(s)
        self.query_one("#op-progress").display = True
        self.progress = s

    def _end_progress(self, line: str = "") -> None:
        """The counter finished (the tool moved on): keep its last value as one log line."""
        if not self.progress:
            return
        if self.progress != line.strip():
            self.query_one("#op-log", RichLog).write(Text(self.progress, style="dim"))
        self.progress = ""
        self.query_one("#op-progress").display = False

    def _done(self, result: Any) -> None:
        self.running = False
        self.dismiss(result)

    def _failed(self, message: str, hint: str, log_file: str, report_path=None) -> None:
        self.running = False
        self._end_progress()
        self.report_path = report_path
        msg = Text()
        msg.append("✘ ", style="bold red")
        msg.append(message, style="bold")
        if hint:
            msg.append(f"\n  {hint}", style="yellow")
        if log_file:
            msg.append(f"\n  Full log: {log_file}", style="dim")
        if report_path:
            msg.append("\n\n" + report.notice(report_path, has_hint=bool(hint)).replace("\n", "\n  "), style="cyan")
        self.query_one("#op-step", Static).update(msg)
        self.query_one("#cancel").display = False
        self.query_one("#retry").display = True
        self.query_one("#copy-report").display = bool(report_path)
        self.query_one("#back").display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.cancel.set()
            self.query_one("#op-step", Static).update("Cancelling… (cleaning up child processes)")
        elif event.button.id == "retry":
            self.query_one("#copy-report").display = False
            self.start()
        elif event.button.id == "copy-report" and self.report_path:
            copy_report(self.app, self.report_path)
        elif event.button.id == "back":
            self.dismiss(None)

    def action_back(self) -> None:
        if self.running:
            self.notify("Still working. Press Cancel to stop it first.", severity="warning")
        else:
            self.dismiss(None)
