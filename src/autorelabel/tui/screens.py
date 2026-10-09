"""Home, setup wizard, doctor, settings, lab and history screens."""

from __future__ import annotations

import json
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Input,
    Label,
    OptionList,
    RadioButton,
    RadioSet,
    Static,
    Switch,
)
from textual.widgets.option_list import Option

from .. import box, config, doctor, hostinfo, paths
from .. import session as S
from ..fsutil import disk_free_bytes
from .common import Banner, Confirm, Message, OperationScreen, Tagline

STATUS_STYLE = {doctor.Status.OK: ("✔", "green"), doctor.Status.WARN: ("!", "yellow"),
                doctor.Status.FAIL: ("✘", "red"), doctor.Status.INFO: ("•", "cyan")}


# --------------------------------------------------------------------------- Home
class HomeScreen(Screen[None]):
    BINDINGS = [("q", "app.quit", "Quit"), ("d", "doctor", "Doctor"), ("s", "settings", "Settings")]

    def compose(self) -> ComposeResult:
        yield Banner(id="banner")
        yield Tagline(id="tagline")
        with Vertical(id="home-body"):
            yield OptionList(id="menu")
            yield Static(id="home-info")
        yield Static(id="statusline")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_menu()

    def on_screen_resume(self) -> None:
        self.refresh_menu()

    def refresh_menu(self) -> None:
        sess = S.current()
        menu = self.query_one("#menu", OptionList)
        menu.clear_options()
        if sess and sess.state not in (S.GRADED,):
            label = {S.IN_PROGRESS: "Return to your exam", S.READY: "Start your prepared exam",
                     S.INTERRUPTED: "Resume your interrupted exam", S.LOCKED: "See grading",
                     S.GRADING: "See grading", S.GRADING_INTERRUPTED: "Finish grading",
                     S.PROVISION_FAILED: "Retry preparing the lab"}.get(sess.state, "Continue session")
            menu.add_option(Option(f"▶  {label}  ({sess.exam.upper()}, {sess.mode})", id="resume"))
        if sess and sess.state == S.GRADED:
            menu.add_option(Option("▶  Results of your last exam", id="results"))
        menu.add_option(Option("🎯 New RHCSA exam  (20 tasks · 180 min · graded after reboot)", id="new-rhcsa"))
        menu.add_option(Option("🧪 New RHCE exam   (20 tasks · 240 min · graded after reboot)", id="new-rhce"))
        menu.add_option(Option("🛠  Practice RHCSA: pick tasks (untimed)", id="practice-rhcsa"))
        menu.add_option(Option("🛠  Practice RHCE: pick tasks (untimed)", id="practice-rhce"))
        menu.add_option(Option("📈 Progress and history", id="history"))
        menu.add_option(Option("🖥  Lab and box", id="lab"))
        menu.add_option(Option("🩺 Doctor (check this host)", id="doctor"))
        menu.add_option(Option("⚙  Settings", id="settings"))
        menu.add_option(Option("🧹 Uninstall (how to)", id="uninstall"))
        menu.add_option(Option("⏻  Quit", id="quit"))
        menu.highlighted = 0
        menu.focus()
        st = config.load()
        ok, msg = box.box_status(st, st.provider) if st.provider else (False, "")
        info = Text()
        info.append("Provider ", style="dim")
        info.append(st.provider or "-", style="bold")
        info.append("   Profile ", style="dim")
        info.append(st.profile, style="bold")
        info.append("   Scoring ", style="dim")
        info.append(st.scoring, style="bold")
        info.append("\nBox ", style="dim")
        info.append("ready" if ok else "not built", style="green" if ok else "yellow")
        info.append(f"  {msg}", style="dim")
        self.query_one("#home-info", Static).update(info)
        storage = paths.storage_root(st.storage_dir) if st.storage_dir else "-"
        self.query_one("#statusline", Static).update(f" {hostinfo.distro().pretty} · lab storage: {storage}")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        oid = event.option.id
        app = self.app
        if oid == "quit":
            app.exit()
        elif oid == "doctor":
            self.action_doctor()
        elif oid == "settings":
            self.action_settings()
        elif oid == "lab":
            app.push_screen(LabScreen())
        elif oid == "history":
            app.push_screen(HistoryScreen())
        elif oid == "uninstall":
            app.push_screen(Message("Uninstall", (
                "To remove everything autorelabel created on this host (VMs, networks, storage pool,\n"
                "the Vagrant box, lab storage, .workspace and .venv), quit and run:\n\n"
                "    ./autorelabel uninstall --dry-run     (shows what will be removed)\n"
                "    ./autorelabel uninstall\n\n"
                "Your ISO is kept. The uninstaller prints undo commands for anything you\n"
                "installed yourself with sudo.")))
        elif oid in ("new-rhcsa", "new-rhce"):
            app.start_new_exam(oid.split("-", 1)[1])
        elif oid == "resume":
            app.resume_session()
        elif oid == "results":
            app.show_results(S.current())
        elif oid in ("practice-rhcsa", "practice-rhce"):
            from .exam import PracticePicker

            app.push_screen(PracticePicker(oid.split("-", 1)[1]))

    def action_doctor(self) -> None:
        self.app.push_screen(DoctorScreen())

    def action_settings(self) -> None:
        self.app.push_screen(SettingsScreen())


# --------------------------------------------------------------------------- Doctor
class DoctorScreen(Screen[bool]):
    BINDINGS = [("escape", "back", "Back"), ("r", "recheck", "Re-check"), ("c", "copy", "Copy fix")]

    def __init__(self, wizard: bool = False):
        super().__init__()
        self.wizard = wizard
        self.checks: list[doctor.Check] = []

    def compose(self) -> ComposeResult:
        yield Static("Host check", classes="title")
        yield Static("Checking this host… (read-only, nothing is changed)", id="doctor-summary")
        yield DataTable(id="doctor-table", cursor_type="row", zebra_stripes=True)
        yield Static(id="doctor-fix")
        with Horizontal(id="form-buttons"):
            yield Button("Re-check", id="recheck")
            yield Button("Continue", id="continue", variant="primary", disabled=True)
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        t = self.query_one(DataTable)
        t.add_columns(" ", "Check", "Details")
        self.query_one("#continue").display = self.wizard
        self.run_checks()

    @work(thread=True, exclusive=True)
    def run_checks(self) -> None:
        checks = doctor.run(config.load())
        self.app.call_from_thread(self.show, checks)

    def show(self, checks: list[doctor.Check]) -> None:
        self.checks = checks
        t = self.query_one(DataTable)
        t.clear()
        for c in checks:
            sym, color = STATUS_STYLE[c.status]
            t.add_row(Text(sym, style=f"bold {color}"), c.title, Text(c.detail, style="dim"), key=c.id)
        blocking = doctor.blocking(checks)
        summary = self.query_one("#doctor-summary", Static)
        if blocking:
            summary.update(Text(f"{len(blocking)} problem(s) to fix. Select a row to see the commands for "
                                f"your distribution, run them, then press Re-check.", style="yellow"))
        else:
            summary.update(Text("This host is ready.", style="bold green"))
        self.query_one("#continue", Button).disabled = bool(blocking)
        first = next((c for c in checks if c.fix and c.status in (doctor.Status.FAIL, doctor.Status.WARN)), None)
        self.show_fix(first)

    def show_fix(self, c: doctor.Check | None) -> None:
        box_ = self.query_one("#doctor-fix", Static)
        if not c or not c.fix:
            box_.update(Text("Select a row with ✘ or ! to see how to fix it.", style="dim"))
            return
        t = Text()
        t.append(f"{c.title}: run these commands yourself (press c to copy):\n", style="bold")
        for line in c.fix:
            t.append(line + "\n", style="dim" if line.startswith("#") else "")
        if c.undo:
            t.append("\nTo undo later: " + " ; ".join(c.undo), style="dim italic")
        box_.update(t)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        key = event.row_key.value if event.row_key else None
        self.show_fix(next((c for c in self.checks if c.id == key), None))

    def action_copy(self) -> None:
        t = self.query_one(DataTable)
        if t.cursor_row is None or not self.checks:
            return
        c = self.checks[t.cursor_row]
        if c.fix:
            self.app.copy_to_clipboard("\n".join(line for line in c.fix if not line.startswith("#")))
            self.notify("Commands copied to the clipboard.")

    def action_recheck(self) -> None:
        self.query_one("#doctor-summary", Static).update("Checking…")
        self.run_checks()

    def action_back(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "recheck":
            self.action_recheck()
        elif event.button.id == "continue":
            self.dismiss(True)
        else:
            self.dismiss(False)


# --------------------------------------------------------------------------- Setup wizard
def _iso_candidates() -> list[Path]:
    seen: list[Path] = []
    for d in (paths.ROOT, Path.home() / "Downloads", paths.ROOT.parent, Path.home()):
        try:
            for p in sorted(d.glob("rhel-10*.iso")):
                if p.is_file() and p.resolve() not in seen:
                    seen.append(p.resolve())
        except OSError:
            continue
    return seen


def _storage_suggestions() -> list[Path]:
    out = [paths.ROOT.parent, Path.home()]
    return [p for i, p in enumerate(out) if p not in out[:i]]


class SetupScreen(Screen[bool]):
    """One-page setup: provider, lab storage, ISO, profile. Doctor runs before it."""

    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, usable: list[str]):
        super().__init__()
        self.usable = usable

    def compose(self) -> ComposeResult:
        st = config.load()
        with VerticalScroll(id="form"):
            yield Static("Setup", classes="title")
            yield Static("A few choices, each with a sensible default. You can change them later in Settings.",
                         classes="muted")
            yield Label("Hypervisor", classes="field-label")
            with RadioSet(id="provider"):
                for p in ("libvirt", "virtualbox"):
                    label = {"libvirt": "libvirt / KVM (recommended)", "virtualbox": "VirtualBox"}[p]
                    yield RadioButton(label + ("" if p in self.usable else "  (not available on this host)"),
                                      value=(p == (st.provider or (self.usable[0] if self.usable else "libvirt"))),
                                      id=f"prov-{p}", disabled=p not in self.usable)
            yield Label("Lab storage directory", classes="field-label")
            yield Static("VM disks and build files go into an 'autorelabel' folder inside this directory "
                         "(~30 GB). Pick a disk with space; /var/lib/libvirt is never used.", classes="field-help")
            default_storage = st.storage_dir or str(_storage_suggestions()[0])
            yield Input(value=default_storage, id="storage")
            yield Static(id="storage-info", classes="field-help")
            yield Label("RHEL 10 DVD ISO", classes="field-label")
            isos = _iso_candidates()
            default_iso = st.iso_path or (str(isos[0]) if isos else "")
            yield Static("Download the 'Red Hat Enterprise Linux 10 Binary DVD' (x86_64) with a free Red Hat "
                         "Developer account. Paste its path here.", classes="field-help")
            yield Input(value=default_iso, placeholder="/path/to/rhel-10.x-x86_64-dvd.iso", id="iso")
            yield Static(id="iso-info", classes="field-help")
            yield Label("Resource profile", classes="field-label")
            with RadioSet(id="profile"):
                yield RadioButton("lite: about 3 GB RAM for RHCSA (recommended)", value=st.profile == "lite",
                                  id="prof-lite")
                yield RadioButton("standard: about 4 GB RAM for RHCSA, more headroom", value=st.profile == "standard",
                                  id="prof-standard")
        with Horizontal(id="form-buttons"):
            yield Button("Save and continue", id="save", variant="primary")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.validate_storage(self.query_one("#storage", Input).value)
        self.validate_iso(self.query_one("#iso", Input).value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "storage":
            self.validate_storage(event.value)
        elif event.input.id == "iso":
            self.validate_iso(event.value)

    def validate_storage(self, value: str) -> bool:
        info = self.query_one("#storage-info", Static)
        p = Path(value).expanduser()
        if not value or not p.is_dir():
            info.update(Text("✘ directory does not exist", style="red"))
            return False
        free = disk_free_bytes(p) / 1e9
        style = "green" if free >= 30 else "yellow"
        info.update(Text(f"✔ {free:.0f} GB free · data goes into {p.resolve() / 'autorelabel'}", style=style))
        return True

    def validate_iso(self, value: str) -> bool:
        info = self.query_one("#iso-info", Static)
        p = Path(value).expanduser()
        if not value or not p.is_file():
            info.update(Text("✘ file not found", style="red"))
            return False
        ver = hostinfo.rhel_version_from_iso(hostinfo.iso_volume_id(p))
        if not ver or not ver.startswith("10."):
            info.update(Text("✘ not a RHEL 10 DVD ISO", style="red"))
            return False
        info.update(Text(f"✔ RHEL {ver} DVD", style="green"))
        return True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss(False)
            return
        storage = self.query_one("#storage", Input).value
        iso = self.query_one("#iso", Input).value
        if not (self.validate_storage(storage) and self.validate_iso(iso)):
            self.notify("Please fix the highlighted fields.", severity="error")
            return
        prov_btn = self.query_one("#provider", RadioSet).pressed_button
        prof_btn = self.query_one("#profile", RadioSet).pressed_button
        st = config.load()
        st.provider = (prov_btn.id or "prov-libvirt").removeprefix("prov-") if prov_btn else "libvirt"
        st.profile = (prof_btn.id or "prof-lite").removeprefix("prof-") if prof_btn else "lite"
        st.storage_dir = str(Path(storage).expanduser().resolve())
        st.iso_path = str(Path(iso).expanduser().resolve())
        config.save(st)
        self.dismiss(True)

    def action_back(self) -> None:
        self.dismiss(False)


# --------------------------------------------------------------------------- Settings
class SettingsScreen(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        st = config.load()
        with VerticalScroll(id="form"):
            yield Static("Settings", classes="title")
            yield Label("Scoring", classes="field-label")
            yield Static("partial: each check earns its share of the task's points · strict: all-or-nothing per task",
                         classes="field-help")
            with RadioSet(id="scoring"):
                yield RadioButton("partial credit (default)", value=st.scoring == "partial", id="sc-partial")
                yield RadioButton("strict (all or nothing)", value=st.scoring == "strict", id="sc-strict")
            yield Label("Show task difficulty during the exam", classes="field-label")
            yield Switch(value=st.show_difficulty_during_exam, id="showdiff")
            yield Label("Forgive host downtime (pause the clock if the host sleeps or crashes)",
                        classes="field-label")
            yield Switch(value=st.forgive_downtime, id="forgive")
            yield Label("Warnings before the end (minutes, comma-separated)", classes="field-label")
            yield Input(value=",".join(str(m) for m in st.warnings_minutes), id="warnings")
            yield Label("Resource profile", classes="field-label")
            with RadioSet(id="profile"):
                yield RadioButton("lite", value=st.profile == "lite", id="p-lite")
                yield RadioButton("standard", value=st.profile == "standard", id="p-standard")
            yield Label("Lab storage directory", classes="field-label")
            yield Input(value=st.storage_dir, id="storage")
            yield Label("RHEL 10 ISO", classes="field-label")
            yield Input(value=st.iso_path, id="iso")
            yield Label("Networks (change only if they collide with yours)", classes="field-label")
            yield Input(value=st.mgmt_subnet, id="mgmt")
            yield Input(value=st.lab_subnet_libvirt, id="labnet")
        with Horizontal(id="form-buttons"):
            yield Button("Save", id="save", variant="primary")
            yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss(None)
            return
        st = config.load()
        sc = self.query_one("#scoring", RadioSet).pressed_button
        st.scoring = "strict" if sc and sc.id == "sc-strict" else "partial"
        st.show_difficulty_during_exam = self.query_one("#showdiff", Switch).value
        st.forgive_downtime = self.query_one("#forgive", Switch).value
        try:
            st.warnings_minutes = sorted({int(x) for x in self.query_one("#warnings", Input).value.split(",")
                                          if x.strip()}, reverse=True)
        except ValueError:
            self.notify("Warnings must be numbers like 30,10,5,1", severity="error")
            return
        pr = self.query_one("#profile", RadioSet).pressed_button
        if pr:
            st.profile = pr.id.removeprefix("p-")
        st.storage_dir = self.query_one("#storage", Input).value
        st.iso_path = self.query_one("#iso", Input).value
        st.mgmt_subnet = self.query_one("#mgmt", Input).value
        st.lab_subnet_libvirt = self.query_one("#labnet", Input).value
        config.save(st)
        self.notify("Settings saved.")
        self.dismiss(None)

    def action_back(self) -> None:
        self.dismiss(None)


# --------------------------------------------------------------------------- Lab
class LabScreen(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Static("Lab and box", classes="title")
        yield Static(id="lab-info", classes="panel")
        with Horizontal(id="form-buttons"):
            yield Button("Build / rebuild box", id="build")
            yield Button("Destroy RHCSA lab", id="destroy", variant="warning")
            yield Button("Refresh", id="refresh")
            yield Button("Back", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_info()

    @work(thread=True, exclusive=True)
    def refresh_info(self) -> None:
        from ..lab import Lab

        st = config.load()
        lines = Text()
        ok, msg = box.box_status(st, st.provider) if st.provider else (False, "no provider")
        lines.append("Box: ", style="bold")
        lines.append(("ready · " if ok else "not ready · ") + msg + "\n", style="green" if ok else "yellow")
        if st.configured:
            lab = Lab(st, "rhcsa")
            for name, (state, reason) in lab.power_states().items():
                v = lab.vm(name)
                color = {"running": "green", "paused": "yellow", "shut off": "dim"}.get(state, "red")
                lines.append(f"  {name:8} ", style="bold")
                lines.append(f"{state:10}", style=color)
                lines.append(f" {reason:10} lab {v.lab_ip:15} mgmt {v.mgmt_ip}\n", style="dim")
        self.app.call_from_thread(self.query_one("#lab-info", Static).update, lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "back":
            self.dismiss(None)
        elif bid == "refresh":
            self.refresh_info()
        elif bid == "build":
            self.app.build_box(then=self.refresh_info)
        elif bid == "destroy":
            def go(yes: bool | None) -> None:
                if not yes:
                    return
                from ..lab import Lab

                def fn(step, line, cancel):
                    step("Destroying the RHCSA lab VMs")
                    Lab(config.load(), "rhcsa").destroy(on_line=line)
                    S.set_current(None)
                self.app.push_screen(OperationScreen("Destroy lab", fn, cancellable=False),
                                     lambda _r: self.refresh_info())
            self.app.push_screen(Confirm("Destroy the RHCSA lab?",
                                         "All lab VMs and their snapshots are deleted. The box, networks and "
                                         "storage pool stay (use uninstall to remove everything).",
                                         yes="Destroy", danger=True), go)

    def action_back(self) -> None:
        self.dismiss(None)


# --------------------------------------------------------------------------- History
class HistoryScreen(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Static("Progress and history", classes="title")
        yield Static(id="hist-summary", classes="panel")
        yield DataTable(id="hist-table", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        from ..bank import load_bank

        t = self.query_one(DataTable)
        t.add_columns("Date", "Exam", "Mode", "Score", "Result")
        rows = []
        try:
            rows = [json.loads(line) for line in paths.HISTORY_FILE.read_text().splitlines() if line.strip()]
        except OSError:
            pass
        import time as _t

        for h in reversed(rows):
            t.add_row(_t.strftime("%Y-%m-%d %H:%M", _t.localtime(h.get("graded_at", 0))), h.get("exam", "").upper(),
                      h.get("mode", ""), f"{h.get('score', 0):.0f}/300",
                      Text("PASS", style="green") if h.get("passed") else Text("FAIL", style="red"))
        bank = load_bank("rhcsa")
        practiced = {o for h in rows if h.get("exam") == "rhcsa" for o in h.get("objectives", {})}
        weak: dict[str, list[float]] = {}
        for h in rows:
            for o, ratio in h.get("objectives", {}).items():
                weak.setdefault(o, []).append(ratio)
        worst = sorted(((sum(v) / len(v), o) for o, v in weak.items()), key=lambda x: x[0])[:5]
        s = Text()
        s.append(f"RHCSA objectives practiced: {len(practiced)}/{len(bank.objectives.objectives)}\n", style="bold")
        s.append(f"Exams taken: {len(rows)}\n")
        if worst:
            s.append("Weakest objectives so far:\n", style="bold")
            for ratio, o in worst:
                text = bank.objectives.objectives.get(o)
                s.append(f"  {ratio * 100:3.0f}%  {text.text if text else o}\n", style="yellow")
        self.query_one("#hist-summary", Static).update(s)

    def action_back(self) -> None:
        self.dismiss(None)

