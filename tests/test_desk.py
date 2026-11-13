"""The Exam Desk. These tests are its release gate: each makes the request an attacker would make
(a foreign Host, a foreign Origin, no code, wrong codes, a missing secret, another user) and expects
the refusal. The shells are a local /bin/sh, so no VM is needed."""

from __future__ import annotations

import asyncio
import hashlib
import http.client
import json
import re
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from autorelabel import localweb, paths
from autorelabel import session as S
from autorelabel.desk import server as desk_server
from autorelabel.desk.server import Desk
from autorelabel.desk.terminals import HIGH_WATER, READ_SIZE, Terminal


# --- a session and an engine without VMs ------------------------------------------------------------
class FakeEngine:
    def __init__(self):
        vm = SimpleNamespace(name="node1", spec=SimpleNamespace(role="node", fqdn="node1.lab.example.com"),
                             lab_ip="172.25.250.11", domain="lab-node1")
        self._lab = SimpleNamespace(vms=[vm], hv=SimpleNamespace(state=lambda domain: ("running", "")))
        self.calls: list[str] = []

    def rendered(self, sess):
        return [{"number": 1, "title": "Task one", "prompt": "Do **this**, with `code`.", "difficulty": "easy",
                 "points": 10, "node": "node1", "console_only": False}]

    def lab(self, exam):
        return self._lab

    def console_login(self, sess, node):
        return "Log in as root, password: redhat"

    def proctor_alive(self, sess):
        return True

    def submit(self, sess):
        self.calls.append("submit")


@pytest.fixture
def sess(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "SESSIONS", tmp_path / "sessions")
    s = S.Session(id="desk-test", exam="rhcsa", mode="exam", seed=1, created=time.time(), state=S.IN_PROGRESS,
                  duration_s=3600, started=time.time())
    s.dir.mkdir(parents=True)
    s.save()
    return s


def make_desk(sess) -> Desk:
    return Desk(engine=FakeEngine(), spawn_argv=lambda kind, node, s: (["/bin/sh"], f"test {kind} on {node}"),
                session_loader=lambda: S.load(sess.id))


def run(desk: Desk, body) -> None:
    async def main():
        task = asyncio.create_task(desk.run())
        await asyncio.wait_for(desk.ready.wait(), 10)
        try:
            await asyncio.wait_for(body(desk), 30)
        finally:
            desk.stop.set()
            await task
    asyncio.run(main())


def http_get(desk: Desk, path: str, host: str | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", desk.port, timeout=5)
    conn.request("GET", path, headers={"Host": host or f"127.0.0.1:{desk.port}"})
    response = conn.getresponse()
    body = response.read()
    conn.close()
    return response, body


def ws(desk: Desk, path: str, origin: str | None = "own"):
    kwargs = {} if origin is None else {"origin": f"http://127.0.0.1:{desk.port}" if origin == "own" else origin}
    return connect(f"ws://127.0.0.1:{desk.port}{path}", open_timeout=5, **kwargs)


async def sign_in(desk: Desk) -> str:
    async with ws(desk, "/ws/control") as c:
        await c.send(json.dumps({"code": desk.code}))
        reply = json.loads(await c.recv())
    assert reply.get("ok") and reply.get("secret")
    return reply["secret"]


async def until(conn, predicate, limit: float = 10.0):
    """Messages from a socket until one satisfies `predicate`; that one is returned."""
    deadline = time.monotonic() + limit
    while True:
        message = await asyncio.wait_for(conn.recv(), max(0.1, deadline - time.monotonic()))
        data = json.loads(message) if isinstance(message, str) else message
        if predicate(data):
            return data


# --- the page and its files -----------------------------------------------------------------------
def test_it_listens_on_loopback_only(sess):
    async def body(desk):
        assert desk_server.HOST == "127.0.0.1" and desk.url.startswith("http://127.0.0.1:")
    run(make_desk(sess), body)


def test_the_page_carries_a_fresh_nonce_and_a_strict_policy(sess):
    async def body(desk):
        seen = set()
        for _ in range(2):
            response, page = await asyncio.to_thread(http_get, desk, "/")
            assert response.status == 200
            policy = response.getheader("Content-Security-Policy")
            nonce = re.search(r"'nonce-([^']+)'", policy).group(1)
            assert f'nonce="{nonce}"' in page.decode()
            assert "unsafe-inline" not in policy and "script-src 'self'" in policy
            assert "frame-ancestors 'none'" in policy
            assert not re.search(rb"<script(?![^>]*\bsrc=)", page)           # no inline script at all
            assert b" style=" not in page
            seen.add(nonce)
        assert len(seen) == 2
    run(make_desk(sess), body)


def test_only_the_fixed_files_are_served(sess):
    async def body(desk):
        for route in desk_server.ROUTES:
            response, _ = await asyncio.to_thread(http_get, desk, route)
            assert response.status == 200, route
            assert response.getheader("X-Content-Type-Options") == "nosniff"
        for path in ("/desk.py", "/../server.py", "/vendor/../server.py", "/static/desk.js", "/ws/term/nope", "/x"):
            response, _ = await asyncio.to_thread(http_get, desk, path)
            assert response.status == 404, path
    run(make_desk(sess), body)


def test_a_foreign_host_name_is_refused(sess):
    async def body(desk):
        response, _ = await asyncio.to_thread(http_get, desk, "/", f"evil.example:{desk.port}")
        assert response.status == 421
    run(make_desk(sess), body)


def test_another_user_of_this_computer_is_refused(sess, monkeypatch):
    monkeypatch.setattr(localweb, "same_user", lambda conn: False)

    async def body(desk):
        response, _ = await asyncio.to_thread(http_get, desk, "/")
        assert response.status == 403
        with pytest.raises(InvalidStatus):
            async with ws(desk, "/ws/control"):
                pass
    run(make_desk(sess), body)


# --- signing in -----------------------------------------------------------------------------------
def test_a_websocket_from_another_page_is_refused(sess):
    async def body(desk):
        for origin in ("http://evil.example", "null", None):
            with pytest.raises(InvalidStatus):
                async with ws(desk, "/ws/control", origin=origin):
                    pass
    run(make_desk(sess), body)


def test_the_code_signs_in_and_the_secret_works_again(sess):
    async def body(desk):
        secret = await sign_in(desk)
        async with ws(desk, "/ws/control") as c:
            await c.send(json.dumps({"secret": secret}))
            assert json.loads(await c.recv()) == {"ok": True}
            state = await until(c, lambda m: "state" in m)
            assert state["state"]["open"] and state["state"]["tasks"][0]["title"] == "Task one"
        lower = desk.code.lower().replace("-", " ")                     # typed carelessly: still the code
        async with ws(desk, "/ws/control") as c:
            await c.send(json.dumps({"code": lower}))
            assert json.loads(await c.recv()).get("secret")
    run(make_desk(sess), body)


def test_three_wrong_codes_end_the_launch(sess):
    async def body(desk):
        for left in (2, 1, 0):
            async with ws(desk, "/ws/control") as c:
                await c.send(json.dumps({"code": "AAAA-AAAA"}))
                assert json.loads(await c.recv()) == {"error": "wrong", "left": left}
        async with ws(desk, "/ws/control") as c:                    # the right code, too late
            await c.send(json.dumps({"code": desk.code}))
            assert json.loads(await c.recv()) == {"error": "used", "left": 0}
        assert not desk.secrets
    run(make_desk(sess), body)


def test_silence_or_rubbish_first_is_shown_the_door(sess):
    async def body(desk):
        async with ws(desk, "/ws/control") as c:                    # says nothing for longer than allowed
            with pytest.raises(ConnectionClosed) as closed:
                await asyncio.wait_for(c.recv(), desk_server.AUTH_TIMEOUT + 3)
            assert closed.value.rcvd.code == 4401
        for first in ("not json", json.dumps(["a"]), json.dumps({"secret": "guess"})):
            async with ws(desk, "/ws/control") as c:
                await c.send(first)
                with pytest.raises(ConnectionClosed):
                    while True:
                        await asyncio.wait_for(c.recv(), 5)
    run(make_desk(sess), body)


# --- shells ---------------------------------------------------------------------------------------
async def open_shell(desk: Desk, secret: str) -> str:
    async with ws(desk, "/ws/control") as c:
        await c.send(json.dumps({"secret": secret}))
        await c.recv()
        await c.send(json.dumps({"do": "shell", "node": "node1"}))
        opened = await until(c, lambda m: "opened" in m or "error" in m)
    assert "opened" in opened, opened
    return opened["opened"]["id"]


async def read_until(term, needle: bytes, limit: float = 10.0) -> bytes:
    seen = b""
    deadline = time.monotonic() + limit
    while needle not in seen:
        message = await asyncio.wait_for(term.recv(), max(0.1, deadline - time.monotonic()))
        if isinstance(message, bytes):
            seen += message
    return seen


def test_a_shell_round_trip_and_its_reattach(sess):
    async def body(desk):
        secret = await sign_in(desk)
        tid = await open_shell(desk, secret)
        async with ws(desk, f"/ws/term/{tid}") as term:
            await term.send(json.dumps({"secret": secret}))
            assert json.loads(await term.recv()) == {"ok": True}
            await term.send(json.dumps({"resize": [120, 40]}))
            await term.send(b"echo autorelabel-$((40+2))\n")
            await read_until(term, b"autorelabel-42")
        async with ws(desk, f"/ws/term/{tid}") as again:              # a reloaded tab: same shell, its output replayed
            await again.send(json.dumps({"secret": secret}))
            assert json.loads(await again.recv()) == {"ok": True}
            await read_until(again, b"autorelabel-42")
            await again.send(b"stty size\n")
            await read_until(again, b"40 120")
    run(make_desk(sess), body)


def test_a_terminal_wants_the_secret_too(sess):
    async def body(desk):
        tid = await open_shell(desk, await sign_in(desk))
        async with ws(desk, f"/ws/term/{tid}") as term:
            await term.send(json.dumps({"code": desk.code}))         # a code is for the control socket only
            with pytest.raises(ConnectionClosed):
                while True:
                    await asyncio.wait_for(term.recv(), 5)
    run(make_desk(sess), body)


def test_shells_are_read_only_once_time_is_up(sess, tmp_path):
    marker = tmp_path / "should-not-exist"

    async def body(desk):
        secret = await sign_in(desk)
        tid = await open_shell(desk, secret)
        s = S.load(sess.id)
        s.transition(S.LOCKED, reason="time")
        await desk.refresh()
        async with ws(desk, f"/ws/term/{tid}") as term:
            await term.send(json.dumps({"secret": secret}))
            await term.recv()
            await term.send(f"touch {marker}\n".encode())
            assert await until(term, lambda m: isinstance(m, dict) and m.get("readOnly"))
            await asyncio.sleep(0.5)
            assert not marker.exists()
        async with ws(desk, "/ws/control") as c:
            await c.send(json.dumps({"secret": secret}))
            await c.recv()
            await c.send(json.dumps({"do": "shell", "node": "node1"}))
            assert "not running" in (await until(c, lambda m: "error" in m))["error"]
    run(make_desk(sess), body)


def test_actions_name_only_this_exams_nodes(sess):
    async def body(desk):
        secret = await sign_in(desk)
        async with ws(desk, "/ws/control") as c:
            await c.send(json.dumps({"secret": secret}))
            await c.recv()
            for action in ({"do": "shell", "node": "../../etc"}, {"do": "reset", "node": "utility"},
                           {"do": "mark", "task": 1, "mark": "<b>"}, {"do": "rm -rf"}):
                await c.send(json.dumps(action))
                assert "error" in await until(c, lambda m: "error" in m)
            await c.send(json.dumps({"do": "mark", "task": 1, "mark": "flag"}))
            state = await until(c, lambda m: "state" in m and m["state"].get("marks"))
            assert state["state"]["marks"] == {"1": "flag"}
        assert S.load(sess.id).marks == {"1": "flag"}
    run(make_desk(sess), body)


# --- the PTY layer on its own ---------------------------------------------------------------------
def test_a_client_that_stops_reading_pauses_the_shell():
    """Flow control: output is read from the PTY only as fast as the slowest tab draws it."""
    async def main():
        loop = asyncio.get_running_loop()
        flood = "head -c 8000000 /dev/zero | tr '\\0' x; echo; echo done"
        term = Terminal("t", "local", "sh", ["/bin/sh", "-c", flood])
        got = bytearray()
        client = term.attach(got.extend)
        term.start(loop)
        for _ in range(100):
            await asyncio.sleep(0.05)
            if term.paused:
                break
        assert term.paused and client.unacked <= HIGH_WATER + READ_SIZE
        held = len(got)
        await asyncio.sleep(0.3)
        assert len(got) == held                                     # nothing more while it isn't acknowledged
        for _ in range(400):
            term.ack(client, client.unacked)
            await asyncio.sleep(0.01)
            if b"done" in got[-64:]:
                break
        assert b"done" in got
        term.close()
    asyncio.run(main())


def test_the_alternate_screen_is_tracked():
    term = Terminal("t", "local", "sh", ["/bin/sh"])
    term._keep(b"hello\x1b[?1049hfull screen")
    assert term.alt_screen
    term._keep(b"\x1b[?1049lback")
    assert not term.alt_screen
    sent: list[bytes] = []
    term.attach(sent.append)
    assert b"hello" in sent[0]


# --- the vendored files ---------------------------------------------------------------------------
def test_the_vendored_files_are_the_recorded_ones():
    vendor = Path(desk_server.STATIC) / "vendor"
    listed = {}
    for line in (vendor / "VENDOR.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2 and re.fullmatch(r"[0-9a-f]{64}", parts[1]):
            listed[parts[0]] = parts[1]
    assert set(listed) == {"xterm.js", "xterm.css", "addon-fit.js"}
    for name, digest in listed.items():
        assert hashlib.sha256((vendor / name).read_bytes()).hexdigest() == digest, name
    for licence in ("xterm-LICENSE.txt", "addon-fit-LICENSE.txt"):
        text = (vendor / licence).read_text()
        assert "MIT" in text or "Permission is hereby granted" in text


def test_the_text_interface_starts_one_desk_and_reuses_it(tmp_path, monkeypatch):
    """w on the exam screen: a second press must not start another desk, or the shells of the
    first would be out of reach."""
    from autorelabel import desk

    monkeypatch.setattr(paths, "SESSIONS", tmp_path / "sessions")
    first = desk.start_in_background()
    try:
        assert desk.start_in_background() is first
        response, page = http_get(first, "/")
        assert response.status == 200 and b"Exam Desk" in page
    finally:
        first.shutdown()
        first.thread.join(10)
        desk._running.clear()


def test_no_task_text_before_the_exam_starts(sess):
    """Reading time is exam time: before the start the page gets the number of tasks, not their text."""
    s = S.load(sess.id)
    s.state = S.READY
    s.save()

    async def body(desk):
        secret = await sign_in(desk)
        async with ws(desk, "/ws/control") as c:
            await c.send(json.dumps({"secret": secret}))
            await c.recv()
            state = (await until(c, lambda m: "state" in m and m["state"].get("open")))["state"]
        assert state["tasks"] == [] and state["taskCount"] == 1 and "Task one" not in json.dumps(state)
    run(make_desk(sess), body)


def test_terminal_sockets_get_the_same_checks(sess):
    """Host, Origin and size limits apply to a terminal's socket as to the page's."""
    async def body(desk):
        secret = await sign_in(desk)
        tid = await open_shell(desk, secret)
        response, _ = await asyncio.to_thread(http_get, desk, f"/ws/term/{tid}", f"evil.example:{desk.port}")
        assert response.status == 421
        for origin in ("http://evil.example", None):
            with pytest.raises(InvalidStatus):
                async with ws(desk, f"/ws/term/{tid}", origin=origin):
                    pass
        async with ws(desk, f"/ws/term/{tid}") as term:
            await term.send(json.dumps({"secret": secret}))
            await term.recv()
            await term.send(json.dumps({"resize": [100000, -5]}))
            await term.send('{"ack": Infinity, "resize": [NaN, 3]}')         # ignored, not fatal
            await term.send(json.dumps(["not", "a", "dict"]))
            await asyncio.sleep(0.3)
            assert (desk.terminals[tid].cols, desk.terminals[tid].rows) == (500, 2)
            await term.send(b"x" * (300 * 1024))                              # over max_size
            with pytest.raises(ConnectionClosed) as closed:
                while True:
                    await asyncio.wait_for(term.recv(), 5)
            assert closed.value.rcvd.code == 1009
        async with ws(desk, "/ws/control") as c:                                # not ASCII: refused, not a crash
            await c.send(json.dumps({"secret": "s\u00e9cret"}))
            with pytest.raises(ConnectionClosed) as closed:
                while True:
                    await asyncio.wait_for(c.recv(), 5)
            assert closed.value.rcvd.code == 4401
        async with ws(desk, "/ws/control") as c:
            await c.send(json.dumps({"secret": secret}))
            await c.recv()
            for task in (True, "1", -1, 10**30, 999):
                await c.send(json.dumps({"do": "mark", "task": task, "mark": "done"}))
                assert "error" in await until(c, lambda m: "error" in m)
        assert S.load(sess.id).marks == {}
    run(make_desk(sess), body)


def test_input_the_shell_is_not_reading_waits_without_blocking_the_desk():
    """A paste while a command runs: the PTY takes only some of it. The rest must wait outside the
    event loop's way, or every shell and the clock would freeze until the command ended."""
    async def main():
        loop = asyncio.get_running_loop()
        term = Terminal("t", "local", "sh", ["/bin/sh", "-c", "sleep 2; cat >/dev/null; echo all-read"])
        got = bytearray()
        client = term.attach(got.extend)
        term.start(loop)
        line = b"x" * 99 + b"\n"
        assert term.write(line * 3000 + b"\x04") == "ok"                     # 300 kB, then Ctrl+D
        assert term.pending                                                   # most of it waits
        worst = 0.0
        for _ in range(20):                                                   # the loop keeps its time
            started = loop.time()
            await asyncio.sleep(0.05)
            worst = max(worst, loop.time() - started)
        assert worst < 0.5
        for _ in range(400):
            await asyncio.sleep(0.025)
            term.ack(client, client.unacked)
            if b"all-read" in got:
                break
        assert b"all-read" in got and not term.pending
        assert term.write(b"y" * (2 << 20)) in ("full", "ended")              # over the limit: refused
        term.close()
    asyncio.run(main())


def test_a_used_up_code_gets_a_fresh_desk_from_the_text_interface(tmp_path, monkeypatch):
    from autorelabel import desk

    monkeypatch.setattr(paths, "SESSIONS", tmp_path / "sessions")
    first = desk.start_in_background()
    try:
        first.tries_left = 0
        second = desk.start_in_background()
        assert second is not first and second.tries_left == 3 and not first.thread.is_alive()
    finally:
        for d in desk._running:
            d.shutdown()
            d.thread.join(10)
        desk._running.clear()
