"""The Exam Desk's server: the exam in one browser window, on 127.0.0.1 only.

It is the one autorelabel listener that accepts input, and the input ends in a root shell on a
lab VM. So nothing is trusted for being "local". Every request is checked, in this order:

1. Host is 127.0.0.1:<port> or localhost:<port>. A page that reached us under another name (DNS
   rebinding) gets 421.
2. The program at the other end runs as this user (`localweb.same_user`, from /proc/net/tcp).
   Another user of this computer gets 403, whatever they have seen.
3. A WebSocket upgrade must carry this server's own Origin. Browsers always send it, and truthfully,
   so a foreign web page can't open a shell through the user's browser.
4. Nothing works before the browser proves it saw the code printed in the terminal that started
   the desk (8 characters, three wrong tries end the launch). The code is never on a command line,
   in a URL or in the browser's history. In exchange the page gets a secret that it keeps in
   sessionStorage (scoped to this origin, port included) and sends as the first message on every
   WebSocket. There is no cookie, so nothing is sent by the browser on its own, to us or to any
   other local server.

Static files are a fixed table; no file is served by a name from the request. The page's
Content-Security-Policy allows scripts from this server only and styles from this server or with
the per-response nonce (xterm.js writes <style> elements; desk-boot.js gives them the nonce).

The desk process owns the shells (terminals.py): they survive a closed or reloaded tab and end
with the desk. Input is dropped once the exam is locked.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import secrets
import time
from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path
from typing import Any

from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

from .. import localweb, log
from .. import session as S
from . import state as desk_state
from .terminals import Terminal

_log = log.get("desk")
HOST = "127.0.0.1"
HERE = Path(__file__).parent
STATIC = HERE / "static"
FONTS = HERE.parent / "dashboard" / "fonts"
ROUTES: dict[str, tuple[Path, str]] = {
    "/desk-boot.js": (STATIC / "desk-boot.js", "text/javascript; charset=utf-8"),
    "/desk.js": (STATIC / "desk.js", "text/javascript; charset=utf-8"),
    "/desk.css": (STATIC / "desk.css", "text/css; charset=utf-8"),
    "/vendor/xterm.js": (STATIC / "vendor" / "xterm.js", "text/javascript; charset=utf-8"),
    "/vendor/xterm.css": (STATIC / "vendor" / "xterm.css", "text/css; charset=utf-8"),
    "/vendor/addon-fit.js": (STATIC / "vendor" / "addon-fit.js", "text/javascript; charset=utf-8"),
    "/fonts/jetbrains-400.woff2": (FONTS / "jetbrains-mono-latin-400-normal.woff2", "font/woff2"),
    "/fonts/jetbrains-700.woff2": (FONTS / "jetbrains-mono-latin-700-normal.woff2", "font/woff2"),
    "/fonts/atkinson-400.woff2": (FONTS / "atkinson-hyperlegible-next-latin-400-normal.woff2", "font/woff2"),
    "/fonts/atkinson-700.woff2": (FONTS / "atkinson-hyperlegible-next-latin-700-normal.woff2", "font/woff2"),
    "/fonts/fraunces-650.woff2": (FONTS / "fraunces-650-latin-normal.woff2", "font/woff2"),
}
BASE_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
}
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"    # no 0/O, 1/I/L, U: easy to read and type
CODE_TRIES = 3
AUTH_TIMEOUT = 2.0
MAX_TERMINALS = 12


def csp(nonce: str) -> str:
    return (f"default-src 'self'; script-src 'self'; style-src 'self' 'nonce-{nonce}'; img-src 'self' data:; "
            "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


def make_code() -> str:
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def _normal(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


class Desk:
    """One launch of the Exam Desk. `spawn_argv(kind, node, sess)` builds a terminal's command line;
    tests replace it with a local shell."""

    def __init__(self, port: int = 0, *, engine: Any = None,
                 spawn_argv: Callable[[str, str, S.Session | None], tuple[list[str], str]] | None = None,
                 session_loader: Callable[[], S.Session | None] = S.current):
        self.requested_port = port
        self.port = 0
        self.code = make_code()
        self.tries_left = CODE_TRIES
        self.secrets: set[str] = set()
        self.terminals: dict[str, Terminal] = {}
        self.controls: set[ServerConnection] = set()
        self.engine = engine
        self.spawn_argv = spawn_argv or self._spawn_argv
        self.load_session = session_loader
        self.snapshot: dict[str, Any] = {}
        self.loop: asyncio.AbstractEventLoop | None = None
        self.stop = asyncio.Event()
        self.ready = asyncio.Event()
        self._n = 0
        self._jobs: set[asyncio.Task] = set()       # grading started here, kept until done

    # --- addresses ---------------------------------------------------------------------------------
    @property
    def url(self) -> str:
        return f"http://{HOST}:{self.port}/"

    def _origin_ok(self, origin: str | None) -> bool:
        return origin in (f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}")

    # --- running -----------------------------------------------------------------------------------
    async def run(self, on_ready: Callable[[Desk], None] | None = None) -> None:
        self.loop = asyncio.get_running_loop()
        async with serve(self._handler, HOST, self.requested_port, process_request=self._process_request,
                         compression=None, server_header="autorelabel", max_size=256 * 1024,
                         ping_interval=20, ping_timeout=40) as server:
            self.port = next(iter(server.sockets)).getsockname()[1]
            self.ready.set()
            if on_ready:
                on_ready(self)
            watcher = asyncio.create_task(self._watch())
            try:
                await self.stop.wait()
            finally:
                watcher.cancel()
                for t in list(self.terminals.values()):
                    t.close()

    def shutdown(self) -> None:
        if self.loop:
            self.loop.call_soon_threadsafe(self.stop.set)

    # --- HTTP and the upgrade checks ---------------------------------------------------------------
    def _respond(self, status: HTTPStatus, body: bytes | str, content_type: str,
                 extra: dict[str, str] | None = None) -> Response:
        data = body.encode() if isinstance(body, str) else body
        headers = Headers({**BASE_HEADERS, **(extra or {}), "Content-Type": content_type,
                           "Content-Length": str(len(data)), "Connection": "close"})
        return Response(status.value, status.phrase, headers, data)

    def _refuse(self, status: HTTPStatus, why: str) -> Response:
        return self._respond(status, f"{status.value} {why}\n", "text/plain; charset=utf-8")

    def _process_request(self, connection: ServerConnection, request: Request) -> Response | None:
        if not localweb.host_ok(request.headers.get("Host", ""), self.port):
            return self._refuse(HTTPStatus.MISDIRECTED_REQUEST, "this server only answers as 127.0.0.1")
        sock = connection.transport.get_extra_info("socket") if connection.transport else None
        if sock is None or not localweb.same_user(sock):
            _log.warning("refused a connection from another user of this computer")
            return self._refuse(HTTPStatus.FORBIDDEN, "this Exam Desk belongs to another user of this computer")
        path = request.path.split("?", 1)[0]
        if request.headers.get("Upgrade", "").lower() == "websocket":
            if not self._origin_ok(request.headers.get("Origin")):
                _log.warning("refused a WebSocket from origin %r", request.headers.get("Origin"))
                return self._refuse(HTTPStatus.FORBIDDEN, "not from this page")
            if path == "/ws/control" or (path.startswith("/ws/term/") and path[9:] in self.terminals):
                return None                                    # go on with the handshake
            return self._refuse(HTTPStatus.NOT_FOUND, "no such terminal")
        if path == "/":
            nonce = secrets.token_urlsafe(18)
            page = (STATIC / "desk.html").read_text(encoding="utf-8").replace("{{nonce}}", nonce)
            return self._respond(HTTPStatus.OK, page, "text/html; charset=utf-8",
                                 {"Content-Security-Policy": csp(nonce)})
        if path in ROUTES:
            file, kind = ROUTES[path]
            return self._respond(HTTPStatus.OK, file.read_bytes(), kind,
                                 {"Content-Security-Policy": "default-src 'none'"})
        return self._refuse(HTTPStatus.NOT_FOUND, "no such page")

    # --- WebSockets --------------------------------------------------------------------------------
    async def _authenticate(self, ws: ServerConnection, allow_code: bool) -> bool:
        try:
            first = json.loads(await asyncio.wait_for(ws.recv(), AUTH_TIMEOUT))
        except (TimeoutError, ValueError, ConnectionClosed, TypeError):
            await ws.close(4401, "who are you")
            return False
        secret = str(first.get("secret", "")) if isinstance(first, dict) else ""
        if secret and any(hmac.compare_digest(secret, s) for s in self.secrets):
            await ws.send(json.dumps({"ok": True}))
            return True
        code = str(first.get("code", "")) if isinstance(first, dict) and allow_code else ""
        if code:
            if self.tries_left <= 0:
                await ws.send(json.dumps({"error": "used", "left": 0}))
            elif hmac.compare_digest(_normal(code), _normal(self.code)):
                fresh = secrets.token_urlsafe(32)
                self.secrets.add(fresh)
                await ws.send(json.dumps({"ok": True, "secret": fresh}))
                return True
            else:
                self.tries_left -= 1
                _log.warning("a wrong Exam Desk code was typed (%d tries left)", self.tries_left)
                await ws.send(json.dumps({"error": "wrong", "left": self.tries_left}))
        else:
            await ws.send(json.dumps({"error": "login"}))
        await ws.close(4401, "not signed in")
        return False

    async def _handler(self, ws: ServerConnection) -> None:
        path = ws.request.path.split("?", 1)[0] if ws.request else ""
        if path == "/ws/control":
            if await self._authenticate(ws, allow_code=True):
                await self._control(ws)
        elif path.startswith("/ws/term/"):
            term = self.terminals.get(path[9:])
            if term and await self._authenticate(ws, allow_code=False):
                await self._terminal(ws, term)

    async def _terminal(self, ws: ServerConnection, term: Terminal) -> None:
        queue: asyncio.Queue[bytes] = asyncio.Queue()
        client = term.attach(queue.put_nowait)

        async def pump() -> None:
            while True:
                chunk = await queue.get()
                while not queue.empty() and len(chunk) < 256 * 1024:
                    chunk += queue.get_nowait()
                await ws.send(chunk)

        sender = asyncio.create_task(pump())
        try:
            async for message in ws:
                if isinstance(message, bytes):
                    if not term.write(message):
                        await ws.send(json.dumps({"readOnly": True}))
                    continue
                try:
                    control = json.loads(message)
                except ValueError:
                    continue
                if "ack" in control:
                    term.ack(client, int(control["ack"]))
                if "resize" in control:
                    cols, rows = control["resize"]
                    term.resize(int(cols), int(rows))
        except (ConnectionClosed, TypeError, ValueError):
            pass
        finally:
            sender.cancel()
            term.detach(client)

    async def _control(self, ws: ServerConnection) -> None:
        self.controls.add(ws)
        try:
            await ws.send(json.dumps({"state": self.public_state()}))
            async for message in ws:
                try:
                    action = json.loads(message)
                except (ValueError, TypeError):
                    continue
                if isinstance(action, dict):
                    reply = await self._act(action)
                    if reply:
                        await ws.send(json.dumps(reply))
        except ConnectionClosed:
            pass
        finally:
            self.controls.discard(ws)

    # --- the exam ----------------------------------------------------------------------------------
    def _engine(self) -> Any:
        if self.engine is None:
            from ..engine import Engine

            self.engine = Engine()
        return self.engine

    def _spawn_argv(self, kind: str, node: str, sess: S.Session | None) -> tuple[list[str], str]:
        """The same command lines the text interface runs, and the hint it prints first."""
        assert sess is not None
        eng = self._engine()
        lab = eng.lab(sess.exam)
        vm = lab.vm(node)
        if kind == "console":
            hint = f"Serial console of {node}. {eng.console_login(sess, node)} Press Enter for a prompt."
            return lab.hv.console_command(vm.domain), hint
        user = "student" if sess.exam == "rhce" and node == "control" else "root"
        argv = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
                f"{user}@{vm.lab_ip}"]
        return argv, f"SSH to {node} as {user}."

    def _read_only(self) -> bool:
        return self.snapshot.get("state") != S.IN_PROGRESS

    def open_terminal(self, kind: str, node: str) -> Terminal:
        if len([t for t in self.terminals.values() if not t.exited]) >= MAX_TERMINALS:
            raise ValueError(f"at most {MAX_TERMINALS} shells at once: close one first")
        sess = self.load_session()
        argv, hint = self.spawn_argv(kind, node, sess)
        self._n += 1
        tid = f"{node}-{kind}-{self._n}-{secrets.token_hex(3)}"
        title = f"{'console' if kind == 'console' else 'shell'} {self._n}"
        term = Terminal(tid, node, kind, argv, title=title, read_only=self._read_only)
        term._keep(f"\x1b[2m{hint}\x1b[0m\r\n".encode())
        assert self.loop is not None
        term.start(self.loop)
        self.terminals[tid] = term
        return term

    async def _act(self, action: dict[str, Any]) -> dict[str, Any] | None:
        do = action.get("do")
        sess = self.load_session()
        try:
            if do == "state":
                return {"state": self.public_state()}
            if sess is None:
                return {"error": "No exam is open."}
            nodes = {n["name"] for n in self.snapshot.get("nodes", [])}
            node = str(action.get("node", ""))
            if do in ("shell", "console", "reset") and node not in nodes:
                return {"error": f"no node {node!r} in this exam"}
            if do == "mark":
                number, mark = str(int(action["task"])), str(action.get("mark", ""))
                if mark not in ("done", "flag", ""):
                    return {"error": "unknown mark"}
                if mark:
                    sess.marks[number] = mark
                else:
                    sess.marks.pop(number, None)
                sess.save()
            elif do == "begin":
                if sess.state == S.READY:
                    await asyncio.to_thread(self._engine().start, sess)
            elif do in ("shell", "console"):
                if sess.state != S.IN_PROGRESS:
                    return {"error": "The exam is not running, so no new shell can be opened."}
                term = self.open_terminal(do, node)
                await self.refresh()
                return {"opened": term.describe()}
            elif do == "close":
                term = self.terminals.pop(str(action.get("terminal", "")), None)
                if term:
                    term.close()
            elif do == "reset":
                if sess.state != S.IN_PROGRESS:
                    return {"error": "The exam is not running."}
                await self._broadcast({"busy": f"Resetting {node} to the exam's starting point…"})
                await asyncio.to_thread(self._engine().reset_to_start, sess, node)
                await self._broadcast({"busy": ""})
            elif do == "end":
                if sess.state in (S.IN_PROGRESS, S.INTERRUPTED):
                    eng = self._engine()
                    await asyncio.to_thread(eng.submit, sess)
                    if not await asyncio.to_thread(eng.proctor_alive, sess):
                        job = asyncio.create_task(asyncio.to_thread(eng.grade, S.load(sess.id)))
                        self._jobs.add(job)
                        job.add_done_callback(self._jobs.discard)
            elif do == "code":
                url = await asyncio.to_thread(self._engine().code_server_url, sess)
                return {"codeServer": url}
            else:
                return {"error": "unknown action"}
        except Exception as exc:          # an action must not take the desk down
            _log.exception("desk action %r failed", do)
            return {"error": f"That did not work: {exc}"}
        await self.refresh()
        return None

    # --- state for the page ------------------------------------------------------------------------
    def public_state(self) -> dict[str, Any]:
        return {**self.snapshot, "terminals": [t.describe() for t in self.terminals.values()]}

    async def _broadcast(self, message: dict[str, Any]) -> None:
        data = json.dumps(message)
        for ws in list(self.controls):
            with contextlib.suppress(ConnectionClosed):
                await ws.send(data)

    async def refresh(self, with_nodes: bool = False) -> None:
        self.snapshot = await asyncio.to_thread(desk_state.snapshot, self.load_session, self._engine_or_none,
                                                self.snapshot, with_nodes)
        await self._broadcast({"state": self.public_state()})

    def _engine_or_none(self) -> Any:
        try:
            return self._engine()
        except Exception:
            return None

    async def _watch(self) -> None:
        """Push the clock every second and the nodes' power state every few seconds; lock the exam
        at 0:00 if no proctor is there to do it (as the text interface does)."""
        tick = 0
        while True:
            try:
                await self.refresh(with_nodes=tick % 4 == 0)
                if self.snapshot.get("state") == S.IN_PROGRESS and self.snapshot.get("timed") \
                        and self.snapshot.get("remaining", 1) <= 0:
                    sess = self.load_session()
                    eng = self._engine_or_none()
                    if sess and eng and not await asyncio.to_thread(eng.proctor_alive, sess):
                        await asyncio.to_thread(eng.lock, sess, "time")
            except Exception:
                _log.exception("desk refresh failed")
            tick += 1
            await asyncio.sleep(1.0)


def run_forever(desk: Desk, on_ready: Callable[[Desk], None]) -> None:
    """For the command line: until Ctrl+C."""
    started = time.monotonic()
    try:
        asyncio.run(desk.run(on_ready))
    except KeyboardInterrupt:
        _log.info("Exam Desk stopped after %.0f s", time.monotonic() - started)
