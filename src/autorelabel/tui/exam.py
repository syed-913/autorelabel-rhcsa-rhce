"""Exam screens: instructions, the exam itself, grading, results and practice."""

from __future__ import annotations

import subprocess
import time
from typing import Any

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Label,
    ListItem,
    ListView,
    Markdown,
    OptionList,
    ProgressBar,
    SelectionList,
    Static,
)
from textual.widgets.option_list import Option

from .. import session as S
from ..engine import Engine
from ..fsutil import read_json
from .common import Confirm, Message

BADGE = {"easy": ("easy", "green"), "medium": ("medium", "yellow"), "hard": ("hard", "red")}


def fmt_clock(seconds: float) -> str:
    seconds = int(max(0, seconds))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


# --------------------------------------------------------------------------- Instructions
class InstructionsScreen(Screen[bool]):
    """Shown before the timer starts (and on demand during the exam)."""

    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, sess: S.Session, before_start: bool = True):
        super().__init__()
        self.sess = sess
        self.before_start = before_start

    def compose(self) -> ComposeResult:
        eng = Engine()
        info = eng.candidate_info(self.sess)
        lines = [f"# {self.sess.exam.upper()} {'exam' if self.sess.mode == 'exam' else 'practice'} instructions", ""]
        if self.sess.duration_s:
            lines += [f"- You have **{self.sess.duration_s // 60} minutes** for **{len(self.sess.tasks)} tasks** "
                      f"({sum(t['points'] for t in self.sess.tasks)} points; 210 to pass).",
                      "- The clock starts when you press **Start**. You'll get warnings before the end; at "
                      "zero the lab is **frozen** and graded automatically."]
        lines += [
            "- **Every node is rebooted before grading.** Only what survives the reboot counts.",
            "- Tasks may depend on each other (e.g. software repositories); do the first tasks first.",
            "",
            "## Your systems",
            "",
            "| Node | Name | Address | root password |",
            "|---|---|---|---|",
        ]
        for n in info["nodes"]:
            pw = f"`{n['root_password']}`" if n["root_password"] else "**unknown: see the tasks**"
            lines.append(f"| {n['name']} | {n['fqdn']} | {n['ip']} | {pw} |")
        if info["exam"] == "rhce":
            acc, ctl = info["accounts"], info["control"]
            lines += [
                "",
                f"Network {info['network']} · DNS {info['dns']} · utility server `{info['utility']}` "
                "(repositories, Git, Ansible content).",
                "",
                "## Accounts",
                "",
                f"- **Work on `control` as `{ctl['user']}`** (password `{acc.get('student', '?')}`), in "
                f"`{ctl['project_dir']}`. `{ctl['user']}` may use sudo.",
                f"- Managed nodes have a user **`ansible`** with the password `{acc.get('ansible', '?')}`.",
                f"- Git repository: `{info['git_url']}` (user `{ctl['user']}`, same password).",
            ]
            if info.get("code_server"):
                lines.append(f"- VS Code in your browser (code-server): **{info['code_server']}** "
                             f"(password: the `{ctl['user']}` password).")
            lines += ["", "## Inventory groups", "", info["inventory_md"]]
            how = (f"- From another terminal: `./autorelabel ssh control` (as {ctl['user']}), "
                   "`./autorelabel ssh node1` (as root) or `./autorelabel console node1` "
                   "(serial console; **Ctrl+]** to leave).")
        else:
            lines += [
                "",
                f"Network {info['network']} · gateway {info['gateway']} · DNS {info['dns']} · "
                f"utility server `{info['utility']}` (repositories, NTP, NFS, Flatpak).",
            ]
            how = ("- From another terminal: `./autorelabel ssh node1` (as root) or `./autorelabel console node1` "
                   "(serial console: GRUB, emergency mode; **Ctrl+]** to leave).")
        lines += [
            "",
            "## How to work",
            "",
            how,
            "- From this screen: select a node in the bottom bar and press **s** (SSH) or **c** (console); "
            "you return here when you exit.",
            "",
            "## Rules",
            "",
            "- Do **not** modify the `mgmt0` interface, the `vagrant` account or its sudo rule: they are how "
            "your work is graded.",
            "- Don't touch the utility server.",
        ]
        with VerticalScroll():
            yield Markdown("\n".join(lines))
        with Horizontal(id="form-buttons"):
            if self.before_start:
                yield Button("Start the exam" if self.sess.duration_s else "Start", id="start", variant="success")
            yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "start")

    def action_back(self) -> None:
        self.dismiss(False)


# --------------------------------------------------------------------------- Node actions
class NodeMenu(ModalScreen[str | None]):
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, node: str, state: str, user: str = "root"):
        super().__init__()
        self.node, self.state, self.user = node, state, user

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"{self.node}: {self.state}", classes="title")
            ol = OptionList(
                Option(f"SSH as {self.user} (returns here when you exit)", id="ssh"),
                Option("Serial console (GRUB, emergency mode; Ctrl+] to leave)", id="console"),
                Option("Power on", id="power-on"),
                Option("Reset (hard reboot, like pressing the reset button)", id="reset"),
                Option("Reset to exam start (LOSES all work on this node)", id="reset-to-start"),
                Option("Cancel", id="cancel"),
            )
            yield ol

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(None if event.option.id == "cancel" else event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)


# --------------------------------------------------------------------------- Exam
class ExamScreen(Screen[None]):
    BINDINGS = [
        Binding("d", "mark('done')", "Done"),
        Binding("f", "mark('flag')", "Flag"),
        Binding("n", "node", "Node actions"),
        Binding("i", "instructions", "Instructions"),
        Binding("k", "check(False)", "Check now", show=False),
        Binding("r", "check(True)", "Check w/ reboot", show=False),
        Binding("v", "solution", "Solution", show=False),
        Binding("x", "submit", "Submit"),
        Binding("escape", "leave", "Home (exam keeps running)"),
    ]

    def __init__(self, sess: S.Session):
        super().__init__()
        self.sess = sess
        self.engine = Engine()
        self.tasks = self.engine.rendered(sess)
        self.practice = sess.mode != "exam"
        self.node_names = [n["name"] for n in self.engine.candidate_info(sess)["nodes"]]
        self.node_index = 0
        self.warned: set[int] = set()

    def compose(self) -> ComposeResult:
        with Horizontal(id="exam-header"):
            yield Static(id="exam-title")
            yield Static(id="exam-clock")
        yield Static(id="exam-banner")
        with Horizontal(id="exam-body"):
            yield ListView(id="task-list")
            with VerticalScroll(id="task-view"):
                yield Markdown(id="task-md")
        yield Static(id="node-bar")
        yield Footer()

    def on_mount(self) -> None:
        lst = self.query_one("#task-list", ListView)
        for t in self.tasks:
            lst.append(ListItem(Label(self._task_label(t)), id=f"t{t['number']}"))
        lst.index = 0
        lst.focus()
        if self.practice:
            self.notify("Practice mode: k = check now, r = check after a reboot, v = show the solution.",
                        timeout=8)
        self.tick()
        self.set_interval(1.0, self.tick)
        self.set_interval(5.0, self.refresh_nodes)
        self.refresh_nodes()

    def _task_label(self, t: dict[str, Any]) -> Text:
        mark = self.sess.marks.get(str(t["number"]), "")
        sym = {"done": "✔ ", "flag": "⚑ "}.get(mark, "  ")
        text = Text()
        text.append(sym, style="green" if mark == "done" else "yellow")
        text.append(f"{t['number']:2}. {t['title']}")
        if self.sess.show_difficulty:
            name, color = BADGE[t["difficulty"]]
            text.append(f"  {name}", style=f"dim {color}")
        return text

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        number = int(event.item.id[1:])
        t = next(x for x in self.tasks if x["number"] == number)
        head = f"## Task {t['number']}: {t['title']}\n\n"
        meta = f"*{t['points']} points"
        if self.sess.show_difficulty:
            meta += f" · {t['difficulty']} · about {t['estimated_minutes']} min"
        meta += f" · on **{t['node']}**"
        if t.get("console_only"):
            meta += " · use the console"
        meta += "*\n\n"
        self.query_one("#task-md", Markdown).update(head + meta + t["prompt"])

    def tick(self) -> None:
        sess = self.sess = S.load(self.sess.id)
        if sess.state in (S.LOCKED, S.GRADING, S.GRADED, S.GRADING_INTERRUPTED):
            self.app.switch_screen(GradingScreen(sess))
            return
        title = f"{sess.exam.upper()} {'EXAM' if sess.mode == 'exam' else 'PRACTICE'} · {len(self.tasks)} tasks"
        done = sum(1 for v in sess.marks.values() if v == "done")
        self.query_one("#exam-title", Static).update(f"{title} · {done} marked done")
        clock = self.query_one("#exam-clock", Static)
        if not sess.duration_s:
            clock.update("untimed")
            return
        rem = sess.remaining()
        clock.update(f"⏱ {fmt_clock(rem)}")
        clock.set_class(rem <= 600, "low")
        clock.set_class(rem <= 120, "critical")
        for m in sorted(sess.warnings_minutes, reverse=True):
            if rem <= m * 60 and m not in self.warned:
                self.warned.add(m)
                self.notify(f"{m} minute{'s' if m != 1 else ''} left.", severity="warning", timeout=10)
                self.app.bell()
        if rem <= 0 and not self.engine.proctor_alive(sess):
            self.engine.lock(sess, reason="time")

    @work(thread=True, exclusive=True, group="nodes")
    def refresh_nodes(self) -> None:
        lab = self.engine.lab(self.sess.exam)
        states = {n: lab.hv.state(lab.vm(n).domain)[0] for n in self.node_names}
        health = read_json(self.sess.dir / "health.json", default={}) or {}
        self.app.call_from_thread(self._show_nodes, states, health)

    def _show_nodes(self, states: dict[str, str], health: dict[str, Any]) -> None:
        bar = Text()
        bar.append("Nodes: ", style="bold")
        for i, n in enumerate(self.node_names):
            st = states.get(n, "?")
            color = {"running": "green", "paused": "yellow", "shut off": "red"}.get(st, "red")
            sel = i == self.node_index
            bar.append(f" {'▸' if sel else ' '}{n} ", style="reverse" if sel else "")
            bar.append(f"● {st}  ", style=color)
        bar.append("   ←/→ select · n actions · ssh/console also from another terminal", style="dim")
        self.query_one("#node-bar", Static).update(bar)
        problems = [n for n, h in (health.get("nodes") or {}).items() if h.get("grader_access") is False]
        banner = self.query_one("#exam-banner", Static)
        if problems:
            banner.update(f"⚠ The grader can no longer reach {', '.join(problems)}: revert changes to mgmt0, "
                          "the vagrant account, sshd or sudo, or those tasks will score 0.")
        banner.set_class(bool(problems), "show")

    def on_key(self, event) -> None:
        if event.key in ("left", "right") and self.node_names:
            self.node_index = (self.node_index + (1 if event.key == "right" else -1)) % len(self.node_names)
            self.refresh_nodes()

    def _current_task(self) -> dict[str, Any] | None:
        lst = self.query_one("#task-list", ListView)
        if lst.index is None:
            return None
        return self.tasks[lst.index]

    def action_mark(self, kind: str) -> None:
        t = self._current_task()
        if not t:
            return
        key = str(t["number"])
        sess = S.load(self.sess.id)
        sess.marks[key] = "" if sess.marks.get(key) == kind else kind
        sess.save()
        self.sess = sess
        lst = self.query_one("#task-list", ListView)
        item = lst.children[lst.index]
        item.query_one(Label).update(self._task_label(t))

    def action_instructions(self) -> None:
        self.app.push_screen(InstructionsScreen(self.sess, before_start=False))

    def action_node(self) -> None:
        if not self.node_names:
            return
        node = self.node_names[self.node_index]
        lab = self.engine.lab(self.sess.exam)
        state = lab.hv.state(lab.vm(node).domain)[0]

        def chosen(action: str | None) -> None:
            if not action:
                return
            if action in ("ssh", "console"):
                self.open_terminal(action, node)
            elif action == "reset-to-start":
                self.app.push_screen(Confirm(f"Reset {node} to the exam start?",
                                             f"Everything you did on {node} is lost. The clock keeps running.",
                                             yes="Reset node", danger=True),
                                     lambda ok: ok and self.node_op(action, node))
            else:
                self.node_op(action, node)

        self.app.push_screen(NodeMenu(node, state, self.ssh_user(node)), chosen)

    def ssh_user(self, node: str) -> str:
        return "student" if self.sess.exam == "rhce" and node == "control" else "root"

    @work(thread=True, group="node-op")
    def node_op(self, action: str, node: str) -> None:
        fn = {"power-on": self.engine.power_on, "reset": self.engine.reset,
              "reset-to-start": self.engine.reset_to_start}[action]
        fn(self.sess, node)
        self.app.call_from_thread(self.notify, f"{node}: {action} done")
        self.refresh_nodes()

    def open_terminal(self, kind: str, node: str) -> None:
        lab = self.engine.lab(self.sess.exam)
        v = lab.vm(node)
        if kind == "ssh":
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                   "-o", "LogLevel=ERROR", f"{self.ssh_user(node)}@{v.lab_ip}"]
            hint = f"SSH to {node} as {self.ssh_user(node)}. Type 'exit' to return to autorelabel."
        else:
            cmd = lab.hv.console_command(v.domain)
            hint = f"Serial console of {node}. Press Enter for a prompt; Ctrl+] returns to autorelabel."
        with self.app.suspend():
            print(f"\n\x1b[1;36m{hint}\x1b[0m\n", flush=True)
            subprocess.run(cmd)

    def action_check(self, reboot: bool) -> None:
        if not self.practice:
            return
        self.notify("Checking your work" + (" (rebooting the nodes first)…" if reboot else "…"))
        self.run_check(reboot)

    @work(thread=True, exclusive=True, group="check")
    def run_check(self, reboot: bool) -> None:
        res = self.engine.grade(self.sess, official=False, reboot=reboot)
        lines = []
        for t in res["tasks"]:
            ok = t["points"] == t["points_possible"]
            lines.append(f"{'✔' if ok else '✘'} Task {t['number']}: {t['points']:g}/{t['points_possible']}")
            for c in t["post"]:
                if c["status"] != "pass":
                    lines.append(f"     ✘ {c['desc']}  {c['detail'][:100]}")
            for cid in t["not_persistent"]:
                lines.append(f"     ⚠ {cid}: worked before the reboot, not after (not persistent)")
        self.app.call_from_thread(self.app.push_screen, Message("Check results (unofficial)", "\n".join(lines)))

    def action_solution(self) -> None:
        if not self.practice:
            return
        t = self._current_task()
        if t:
            md = self.engine.solutions(self.sess).get(t["number"], "")
            self.app.push_screen(SolutionScreen(t["title"], md))

    def action_submit(self) -> None:
        def go(yes: bool | None) -> None:
            if yes:
                self.engine.submit(self.sess)
                self.app.switch_screen(GradingScreen(S.load(self.sess.id)))
        label = "End the exam now and grade it?" if not self.practice else "Finish this practice session?"
        self.app.push_screen(Confirm(label, "The lab is frozen and every node is rebooted before grading. "
                                            "You cannot continue afterwards.", yes="Submit"), go)

    def action_leave(self) -> None:
        if self.sess.duration_s and self.sess.mode == "exam":
            self.notify("The exam keeps running in the background (the clock is ticking).", severity="warning")
        self.app.pop_screen()


class SolutionScreen(Screen[None]):
    BINDINGS = [("escape", "back", "Back")]

    def __init__(self, title: str, md: str):
        super().__init__()
        self.title_text, self.md = title, md

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(self.md or "_No solution notes._")
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


# --------------------------------------------------------------------------- Grading
class GradingScreen(Screen[None]):
    BINDINGS = [("escape", "home", "Home")]

    def __init__(self, sess: S.Session):
        super().__init__()
        self.sess = sess
        self.engine = Engine()

    def compose(self) -> ComposeResult:
        yield Static("Grading", classes="title")
        yield Static("Your exam is locked. Every node is rebooted, then your work is checked.", classes="muted")
        yield Static(id="grade-phase")
        yield ProgressBar(id="grade-bar", total=100, show_eta=False)
        yield Static(id="grade-detail", classes="muted")
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.0, self.poll)
        if not self.engine.proctor_alive(self.sess):
            self.grade_inline()

    @work(thread=True, exclusive=True)
    def grade_inline(self) -> None:
        sess = S.load(self.sess.id)
        if sess.state in (S.LOCKED, S.GRADING_INTERRUPTED):
            from ..fsutil import atomic_write_json

            progress = sess.dir / "grading-progress.json"

            def on_event(kind: str, data: dict[str, Any]) -> None:
                atomic_write_json(progress, {"ts": time.time(), "kind": kind, **data})

            try:
                self.engine.grade(sess, on_event)
                atomic_write_json(progress, {"ts": time.time(), "kind": "done"})
            except Exception as exc:
                atomic_write_json(progress, {"ts": time.time(), "kind": "error", "message": str(exc)})

    def poll(self) -> None:
        sess = S.load(self.sess.id)
        p = read_json(sess.dir / "grading-progress.json", default={}) or {}
        phase = self.query_one("#grade-phase", Static)
        bar = self.query_one("#grade-bar", ProgressBar)
        kind = p.get("kind")
        if kind == "phase":
            phase.update(Text(f"▶ {p.get('label', '')}", style="bold cyan"))
        elif kind == "check":
            bar.update(total=max(1, p.get("total", 1)), progress=p.get("done", 0))
            self.query_one("#grade-detail", Static).update(f"{p.get('phase', '')}: task {p.get('task')} "
                                                           f"· {p.get('check')} → {p.get('status')}")
        elif kind == "reboot":
            self.query_one("#grade-detail", Static).update(f"{p.get('node')}: {p.get('stage')} "
                                                           f"{p.get('message', '')}")
        elif kind == "error":
            phase.update(Text(f"✘ Grading stopped: {p.get('message')}. It will resume where it stopped "
                              "when you open this screen again.", style="red"))
        if sess.state == S.GRADED:
            self.app.switch_screen(ResultsScreen(sess))

    def action_home(self) -> None:
        self.notify("Grading continues in the background.")
        self.app.pop_screen()


# --------------------------------------------------------------------------- Results
class ResultsScreen(Screen[None]):
    BINDINGS = [("escape", "home", "Home"), ("t", "retake", "Retake same exam"), ("v", "solution", "Solution")]

    def __init__(self, sess: S.Session):
        super().__init__()
        self.sess = sess
        self.engine = Engine()
        self.results = read_json(sess.results_file, default={}) or {}
        self.solutions = self.engine.solutions(sess)

    def compose(self) -> ComposeResult:
        r = self.results
        passed = r.get("passed")
        yield Static(f"{r.get('scaled_score', 0):.0f} / {r.get('total_points', 300)}   "
                     f"{'PASS' if passed else 'FAIL'}  (pass mark {r.get('pass_mark', 210)})",
                     id="score", classes="pass" if passed else "fail")
        yield Static(id="breakdown", classes="panel")
        with Horizontal(id="results-body"):
            yield ListView(id="results-tasks")
            with VerticalScroll(id="results-detail"):
                yield Markdown(id="results-md")
        yield Footer()

    def on_mount(self) -> None:
        r = self.results
        b = Text()
        b.append("By difficulty: ", style="bold")
        for d in ("easy", "medium", "hard"):
            v = r.get("by_difficulty", {}).get(d)
            if v:
                b.append(f"{d} {v['points']:g}/{v['possible']}   ", style=BADGE[d][1])
        b.append("\nBy domain: ", style="bold")
        for dom, v in r.get("by_domain", {}).items():
            b.append(f"{dom} {v['points']:g}/{v['possible']}  ")
        if r.get("incidents"):
            b.append("\nIncidents: ", style="bold red")
            for inc in r["incidents"]:
                b.append(f"\n  {inc['node']}: {inc['message']}", style="red")
        self.query_one("#breakdown", Static).update(b)
        lst = self.query_one("#results-tasks", ListView)
        for t in r.get("tasks", []):
            full = t["points"] == t["points_possible"]
            sym, color = ("✔", "green") if full else (("◐", "yellow") if t["points"] else ("✘", "red"))
            label = Text()
            label.append(f"{sym} ", style=color)
            label.append(f"{t['number']:2}. {t['title'][:34]}  ")
            label.append(f"{t['points']:g}/{t['points_possible']}", style=color)
            lst.append(ListItem(Label(label), id=f"r{t['number']}"))
        lst.index = 0
        lst.focus()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        number = int(event.item.id[1:])
        t = next(x for x in self.results["tasks"] if x["number"] == number)
        md = [f"## Task {number}: {t['title']}",
              f"*{t['difficulty']} · {t['points']:g} of {t['points_possible']} points*", ""]
        for c in t["post"]:
            sym = {"pass": "✔", "fail": "✘", "error": "!", "unreachable": "⨯"}[c["status"]]
            line = f"- {sym} {c['desc']}"
            if c["id"] in t["not_persistent"]:
                line += " **(worked before the reboot, not after: not persistent)**"
            if c["status"] != "pass" and c.get("detail"):
                line += f"  \n  `{c['detail'][:160]}`"
            md.append(line)
        md += ["", "---", "", "*Press **v** for the full solution.*"]
        self.query_one("#results-md", Markdown).update("\n".join(md))

    def action_solution(self) -> None:
        lst = self.query_one("#results-tasks", ListView)
        if lst.index is None:
            return
        t = self.results["tasks"][lst.index]
        self.app.push_screen(SolutionScreen(t["title"], self.solutions.get(t["number"], "")))

    def action_retake(self) -> None:
        self.app.retake(self.sess)

    def action_home(self) -> None:
        self.app.pop_to_home()


# --------------------------------------------------------------------------- Practice
class PracticePicker(Screen[None]):
    BINDINGS = [("escape", "back", "Back"), ("enter", "start", "Start")]

    def compose(self) -> ComposeResult:
        from ..bank import load_bank

        bank = load_bank("rhcsa")
        yield Static("Practice: choose tasks (space to select, Enter to start)", classes="title")
        yield Static("Untimed. You can check your work at any time (k) and after a reboot (r), and read the "
                     "solution (v).", classes="muted")
        options = []
        titles = {d.id: d.title for d in bank.objectives.domains}
        for t in sorted(bank.tasks.values(), key=lambda x: (x.domain, x.difficulty, x.id)):
            label = Text()
            label.append(f"[{titles[t.domain][:28]:28}] ", style="dim")
            label.append(t.title)
            name, color = BADGE[t.difficulty]
            label.append(f"  {name}", style=color)
            options.append((label, t.id))
        yield SelectionList[str](*options, id="practice-list")
        with Horizontal(id="form-buttons"):
            yield Button("Start practice", id="start", variant="primary")
            yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            self.action_start()
        else:
            self.app.pop_screen()

    def action_start(self) -> None:
        chosen = list(self.query_one(SelectionList).selected)
        if not chosen:
            self.notify("Select at least one task (space).", severity="warning")
            return
        if len(chosen) > 10:
            self.notify("Pick at most 10 tasks per practice session.", severity="warning")
            return
        self.app.start_practice(chosen)

    def action_back(self) -> None:
        self.app.pop_screen()

