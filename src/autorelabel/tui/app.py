"""The autorelabel TUI application and its navigation flows."""

from __future__ import annotations

from pathlib import Path

from textual.app import App

from .. import box, config, doctor
from .. import session as S
from ..engine import Engine
from .common import Confirm, Message, OperationScreen
from .exam import ExamScreen, GradingScreen, InstructionsScreen, ResultsScreen
from .screens import DoctorScreen, HomeScreen, SetupScreen


class AutorelabelApp(App[None]):
    CSS_PATH = str(Path(__file__).with_name("theme.tcss"))
    TITLE = "autorelabel"
    SUB_TITLE = "RHCSA & RHCE practice exams on RHEL 10"
    ENABLE_COMMAND_PALETTE = False

    def __init__(self, start: str | None = None):
        super().__init__()
        self.start_action = start

    # --- startup ------------------------------------------------------------------------
    def on_mount(self) -> None:
        self.push_screen(HomeScreen())
        st = config.load()
        if not st.configured:
            self.first_run()
            return
        sess = S.current()
        if sess:
            note = Engine().recover(sess)
            if note:
                self.push_screen(Message("Welcome back", note))
        if self.start_action in ("rhcsa", "rhce"):
            self.start_new_exam(self.start_action)
        elif self.start_action == "resume":
            self.resume_session()

    def first_run(self) -> None:
        def after_doctor(ok: bool | None) -> None:
            if not ok:
                return
            checks = doctor.run(config.load())
            usable = doctor.usable_providers(checks) or ["libvirt"]
            self.push_screen(SetupScreen(usable), after_setup)

        def after_setup(ok: bool | None) -> None:
            if ok:
                self.build_box()

        self.push_screen(Message("Welcome to autorelabel",
                                 "First run: checking this host, then a short setup, then the RHEL 10 box is\n"
                                 "built once from your ISO (about 10-15 minutes). After that, exams start in a\n"
                                 "few minutes."), lambda _r: self.push_screen(DoctorScreen(wizard=True), after_doctor))

    # --- box ----------------------------------------------------------------------------
    def build_box(self, then=None) -> None:
        st = config.load()

        def fn(step, line, cancel):
            return box.build(st, st.provider, on_step=step, on_line=line, cancel=cancel)

        def done(result) -> None:
            if result:
                self.notify("The RHEL 10 box is ready.", severity="information")
            if then:
                then()

        self.push_screen(OperationScreen("Building the RHEL 10 box from your ISO", fn), done)

    # --- exams --------------------------------------------------------------------------
    def start_new_exam(self, exam: str) -> None:
        st = config.load()
        ok, msg = box.box_status(st, st.provider)
        if not ok:
            self.push_screen(Confirm("The RHEL 10 box is not ready", f"{msg}.\nBuild it now (about 10-15 min)?",
                                     yes="Build box"), lambda yes: yes and self.build_box())
            return
        current = S.current()
        if current and current.state not in (S.GRADED, S.ABANDONED):
            def replace(yes: bool | None) -> None:
                if yes:
                    Engine().abandon(current)
                    self.start_new_exam(exam)
            self.push_screen(Confirm("Replace the current session?",
                                     f"You have a {current.exam.upper()} session in state '{current.state}'. "
                                     "Starting a new exam abandons it.", yes="Abandon and start new",
                                     danger=True), replace)
            return
        self.with_exam_content(exam, lambda: self._prepare(lambda eng: eng.create(exam, mode="exam"),
                                                            f"Preparing a new {exam.upper()} exam"))

    def with_exam_content(self, exam: str, then) -> None:
        """RHCE needs a one-time download (navigator wheels, collections, code-server)."""
        if exam != "rhce":
            then()
            return
        from .. import content

        st = config.load()
        ok, _msg = content.status(st)
        if ok:
            then()
            return

        def fn(step, line, cancel):
            return content.download(st, on_step=step, on_line=line, with_code_server=st.code_server)

        def done(result) -> None:
            if result:
                then()

        self.push_screen(Confirm("RHCE content is needed once", (
            "The RHCE lab needs ansible-navigator, the ansible.posix and community.general\n"
            "collections" + (" and code-server (VS Code in the browser)" if st.code_server else "") +
            ". They are downloaded once from PyPI, Ansible Galaxy" +
            (", GitHub and Open VSX" if st.code_server else "") + "\n(about 60-150 MB) and kept in the lab "
            "storage. Everything after that works offline."), yes="Download"),
            lambda yes: yes and self.push_screen(OperationScreen("Downloading RHCE content", fn), done))

    def start_practice(self, task_ids: list[str], exam: str = "rhcsa") -> None:
        current = S.current()
        if current and current.state in (S.IN_PROGRESS, S.INTERRUPTED):
            self.notify("Finish or abandon your current exam first.", severity="warning")
            return
        if current and current.state not in (S.GRADED, S.ABANDONED):
            Engine().abandon(current)
        self.with_exam_content(exam, lambda: self._prepare(
            lambda eng: eng.create(exam, mode="practice", task_ids=task_ids, timed=False),
            "Preparing your practice session"))

    def _prepare(self, create, title: str) -> None:
        holder: dict[str, S.Session] = {}

        def fn(step, line, cancel):
            eng = Engine()
            sess = holder.get("s") or create(eng)
            holder["s"] = sess
            if sess.state in (S.NEW, S.PROVISION_FAILED):
                eng.prepare(sess, on_step=step, on_line=line, cancel=cancel)
            return S.load(sess.id)

        def done(sess: S.Session | None) -> None:
            if sess and sess.state == S.READY:
                self.show_instructions(sess)

        self.push_screen(OperationScreen(title, fn), done)

    def show_instructions(self, sess: S.Session) -> None:
        def go(start: bool | None) -> None:
            if start:
                Engine().start(sess)
                self.push_screen(ExamScreen(S.load(sess.id)))
        self.push_screen(InstructionsScreen(sess), go)

    def resume_session(self) -> None:
        sess = S.current()
        if not sess:
            return
        eng = Engine()
        if sess.state == S.IN_PROGRESS:
            self.push_screen(ExamScreen(sess))
        elif sess.state == S.READY:
            self.show_instructions(sess)
        elif sess.state == S.INTERRUPTED:
            def fn(step, line, cancel):
                step("Starting the lab again (your work is kept)")
                eng.resume(sess)
                return S.load(sess.id)
            self.push_screen(OperationScreen("Resuming your exam", fn, cancellable=False),
                             lambda s: s and self.push_screen(ExamScreen(s)))
        elif sess.state in (S.LOCKED, S.GRADING, S.GRADING_INTERRUPTED):
            self.push_screen(GradingScreen(sess))
        elif sess.state == S.PROVISION_FAILED:
            self._prepare(lambda _eng: sess, "Retrying lab preparation")
        elif sess.state == S.GRADED:
            self.show_results(sess)

    def show_results(self, sess: S.Session | None) -> None:
        if sess and sess.results_file.exists():
            self.push_screen(ResultsScreen(sess))

    def retake(self, sess: S.Session) -> None:
        def fn(step, line, cancel):
            step("Restoring the exam starting point")
            return Engine().retake(sess)

        self.push_screen(OperationScreen("Retake: same tasks, fresh start", fn, cancellable=False),
                         lambda s: s and self.show_instructions(s))

    def pop_to_home(self) -> None:
        while len(self.screen_stack) > 2:
            self.pop_screen()
        if not isinstance(self.screen, HomeScreen):
            self.switch_screen(HomeScreen())


def run_tui(start: str | None = None) -> int:
    AutorelabelApp(start).run()
    return 0
