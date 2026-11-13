"""The results dashboard: the numbers (stats), the pages (escaping) and the server's checks.
No VM and no browser: the server is exercised over a real socket on 127.0.0.1."""

from __future__ import annotations

import http.client
import json
import threading

import pytest

from autorelabel import paths, stats
from autorelabel.dashboard import pages, server

OBJECTIVES = {"rhcsa.a.one": ("Do one thing", "Tools"), "rhcsa.a.two": ("Do another", "Tools"),
              "rhcsa.b.three": ("Never tested", "Storage")}
TITLES = {"rhcsa.a.t1": ("First task", "Tools"), "rhcsa.a.t2": ("Second task", "Tools")}
HOSTILE = '<script>alert(1)</script>"><img src=x onerror=alert(2)>'


def _results(session: str, score: float, fail_check: bool, lost: bool = False) -> dict:
    check = {"id": "c1", "desc": "the file exists", "node": "node1", "status": "fail" if fail_check else "pass",
             "weight": 1.0, "covers": ["R1"], "detail": HOSTILE if fail_check else "", "guard": False}
    return {"session": session, "exam": "rhcsa", "mode": "exam", "scoring": "partial", "scaled_score": score,
            "total_points": 300, "pass_mark": 210, "passed": score >= 210, "elapsed_s": 6000, "duration_s": 10800,
            "graded_at": 1_700_000_000, "by_difficulty": {"easy": {"points": 10, "possible": 20}},
            "by_domain": {"tools": {"points": 10, "possible": 20}},
            "incidents": [{"node": "node2", "message": HOSTILE}],
            "tasks": [{"number": 1, "task_id": "rhcsa.a.t1", "title": HOSTILE, "difficulty": "easy", "domain": "tools",
                       "objectives": ["rhcsa.a.one"], "points_possible": 10, "points": 0 if fail_check else 10,
                       "pre": [], "post": [check], "not_persistent": ["c1"] if lost else []}]}


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Six graded attempts: four RHCSA exams (the first from before tasks were recorded), one RHCSA
    practice set, one RHCE exam; plus two lines that cannot be used."""
    sessions = tmp_path / "sessions"
    lines = []
    for i, (score, fail) in enumerate([(150, True), (190, True), (220, True), (260, False)]):
        sid = f"s{i}"
        (sessions / sid).mkdir(parents=True)
        (sessions / sid / "results.json").write_text(json.dumps(_results(sid, score, fail, lost=(i == 1))))
        line = {"session": sid, "exam": "rhcsa", "mode": "exam", "score": score, "passed": score >= 210,
                "graded_at": 1_700_000_000 + i * 86400,
                "objectives": {"rhcsa.a.one": 0.0 if fail else 1.0, "rhcsa.a.two": i / 4},
                "tasks": {"rhcsa.a.t1": 0.0 if fail else 1.0, "rhcsa.a.t2": 1.0}}
        if i == 0:
            del line["tasks"]
        lines.append(line)
    lines.append({"session": "p1", "exam": "rhcsa", "mode": "practice", "score": 300, "passed": True,
                  "graded_at": 1_700_500_000, "objectives": {"rhcsa.a.two": 1.0}, "tasks": {"rhcsa.a.t2": 1.0}})
    lines.append({"session": "e1", "exam": "rhce", "mode": "exam", "score": 100, "passed": False,
                  "graded_at": 1_700_600_000, "objectives": {}, "tasks": {}})
    history = tmp_path / "history.jsonl"
    history.write_text("".join(json.dumps(ln) + "\n" for ln in lines)
                       + 'not json\n{"session": "../../etc", "exam": "rhcsa"}\n\n')
    monkeypatch.setattr(paths, "HISTORY_FILE", history)
    monkeypatch.setattr(paths, "SESSIONS", sessions)
    return tmp_path


# --- the numbers ----------------------------------------------------------------------------------
def test_the_history_is_read_and_bad_lines_are_counted(workspace):
    h = stats.load()
    assert [a.session for a in h.attempts] == ["s0", "s1", "s2", "s3", "p1", "e1"] and h.unreadable == 2
    # the first line has no tasks: they come from the session's results
    assert h.attempts[0].tasks == {"rhcsa.a.t1": 0.0}
    assert [a.session for a in stats.select(h.attempts, "rhcsa", exams_only=True)] == ["s0", "s1", "s2", "s3"]
    assert len(stats.select(h.attempts, "rhcsa")) == 5 and len(stats.select(h.attempts, "rhce")) == 1


def test_no_history_is_no_error(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "HISTORY_FILE", tmp_path / "none.jsonl")
    assert stats.load() == stats.History([], 0)


def test_overview_numbers(workspace):
    o = stats.overview(stats.select(stats.load().attempts, "rhcsa", exams_only=True))
    assert o == {"attempts": 4, "passes": 2, "best": 260, "last": [190, 220, 260], "median_minutes": 100}


def test_objectives_weakest_first_and_never_tested_listed(workspace):
    rows = {r.key: r for r in stats.objective_rows(stats.select(stats.load().attempts, "rhcsa", True), OBJECTIVES)}
    one, two, three = rows["rhcsa.a.one"], rows["rhcsa.a.two"], rows["rhcsa.b.three"]
    assert (one.tested, one.share, one.last_share) == (4, 0.25, 1.0)
    assert one.trend == pytest.approx(0.5)             # last two (0, 1) against the two before (0, 0)
    assert two.share == pytest.approx((0 + 0.25 + 0.5 + 0.75) / 4)
    assert (three.tested, three.share, three.trend, three.last) == (0, None, None, None)
    assert [r.key for r in stats.weakest(list(rows.values()))] == ["rhcsa.a.one", "rhcsa.a.two"]


def test_tasks_and_their_repeated_failures(workspace):
    attempts = stats.select(stats.load().attempts, "rhcsa", True)
    rows = stats.task_rows(attempts, TITLES)
    assert [r.key for r in rows] == ["rhcsa.a.t1", "rhcsa.a.t2"]
    t1 = rows[0]
    assert (t1.title, t1.tested, t1.share, t1.last_share) == ("First task", 4, 0.25, 1.0)
    assert t1.checks == [{"desc": "the file exists", "node": "node1", "guard": False, "seen": 4, "failed": 3,
                          "not_persistent": 1}]
    assert [(r.key, c["failed"]) for r, c in stats.repeated_failures(rows)] == [("rhcsa.a.t1", 3)]
    assert stats.not_persistent_total(attempts) == 1


@pytest.mark.parametrize("session", ["../s0", "s0/../s1", "", "a" * 65, "s0\x00", "s0\n", "/etc/passwd", "none"])
def test_a_session_is_never_looked_up_by_a_path(workspace, session):
    assert stats.session_results(session) is None


# --- the pages ------------------------------------------------------------------------------------
def test_text_from_the_lab_is_escaped_everywhere(workspace):
    h = stats.load()
    out = [pages.overview(h, "rhcsa", False, OBJECTIVES, TITLES),
           pages.objectives_page(h, "rhcsa", False, OBJECTIVES),
           pages.tasks_page(h, "rhcsa", False, {"rhcsa.a.t1": (HOSTILE, HOSTILE)}),
           pages.attempt_page(stats.session_results("s0"), {"tools": HOSTILE})]
    for html in out:
        assert "<script" not in html and "<img" not in html and "onerror=alert(2)>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out[3]
    assert "worked before the reboot" in pages.attempt_page(stats.session_results("s1"), {})


def test_pages_say_so_when_there_is_nothing_yet(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "HISTORY_FILE", tmp_path / "none.jsonl")
    h = stats.load()
    assert "Nothing graded yet" in pages.overview(h, "rhce", False, {}, {})
    assert "No task has been graded yet" in pages.tasks_page(h, "rhce", False, {})


def test_the_pages_follow_the_copy_rules(workspace):
    h = stats.load()
    text = "".join([pages.overview(h, "rhcsa", False, OBJECTIVES, TITLES), pages.tasks_page(h, "rhcsa", False, TITLES),
                    pages.objectives_page(h, "rhcsa", False, OBJECTIVES),
                    pages.attempt_page(_results("x", 1, False), {})])
    for banned in ("—", "–", "instead", "rather"):
        assert banned not in text


# --- the server -----------------------------------------------------------------------------------
@pytest.fixture
def running(workspace, monkeypatch):
    monkeypatch.setattr(server, "bank_names", lambda exam: (OBJECTIVES, TITLES, {"tools": "Tools"}))
    srv = server.Dashboard()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def _request(srv, path, method="GET", host=None, cookie=None):
    conn = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=5)
    headers = {"Host": host or f"127.0.0.1:{srv.port}"}
    if cookie:
        headers["Cookie"] = cookie
    conn.request(method, path, headers=headers)
    response = conn.getresponse()
    body = response.read().decode(errors="replace")
    conn.close()
    return response, body


def _login(srv) -> str:
    response, _ = _request(srv, f"/open/{srv.token}")
    assert response.status == 303 and response.getheader("Location") == "/"
    cookie = response.getheader("Set-Cookie")
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
    return cookie.split(";")[0]


def test_it_listens_on_loopback_only(running):
    assert running.server_address[0] == "127.0.0.1" and server.HOST == "127.0.0.1"


def test_a_foreign_host_name_is_refused(running):
    """DNS rebinding: the browser believes it talks to another site and says so in Host."""
    cookie = _login(running)
    port = running.port
    for host in ("evil.example", f"evil.example:{port}", "127.0.0.1:1", f"127.0.0.1.evil.example:{port}"):
        response, _ = _request(running, "/", host=host, cookie=cookie)
        assert response.status == 421, host
    assert _request(running, "/", host=f"localhost:{running.port}", cookie=cookie)[0].status == 200


def test_nothing_is_shown_without_the_cookie(running):
    for path in ("/", "/objectives", "/tasks", "/attempt/s0", "/style.css"):
        assert _request(running, path)[0].status == 403, path
    assert _request(running, "/", cookie=f"{server.COOKIE}=guess")[0].status == 403
    assert _request(running, "/open/guess")[0].status == 403


def test_the_launch_address_works_once(running):
    cookie = _login(running)
    assert _request(running, f"/open/{running.token}")[0].status == 403            # someone else, later
    assert _request(running, f"/open/{running.token}", cookie=cookie)[0].status == 303   # the same browser, reloading
    assert _request(running, "/", cookie=cookie)[0].status == 200


def test_it_is_read_only(running):
    cookie = _login(running)
    for method in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS"):
        response, _ = _request(running, "/", method=method, cookie=cookie)
        assert response.status == 405 and response.getheader("Allow") == "GET, HEAD", method
    response, body = _request(running, "/", method="HEAD", cookie=cookie)
    assert response.status == 200 and body == ""


def test_pages_and_headers(running):
    cookie = _login(running)
    for path, expect in (("/", "What keeps costing you points"), ("/?exam=rhce", "Overview"),
                         ("/objectives?exam=rhcsa&only=exams", "Never tested"), ("/tasks", "First task"),
                         ("/attempt/s1", "worked before the reboot"), ("/?exam=<script>", "Overview")):
        response, body = _request(running, path, cookie=cookie)
        assert response.status == 200 and expect in body, path
        assert "<script" not in body and " style=" not in body      # nothing inline for the policy to refuse
        csp = response.getheader("Content-Security-Policy")
        assert csp.startswith("default-src 'none'") and "script" not in csp and "frame-ancestors 'none'" in csp
        assert response.getheader("X-Content-Type-Options") == "nosniff"
        assert response.getheader("Cache-Control") == "no-store"
        assert response.getheader("Referrer-Policy") == "no-referrer"
    response, body = _request(running, "/style.css", cookie=cookie)
    assert response.status == 200 and response.getheader("Content-Type").startswith("text/css")
    assert "prefers-reduced-motion" in body
    assert "font-src 'self'" in response.getheader("Content-Security-Policy")
    for font in server.FONTS:
        response, _ = _request(running, font, cookie=cookie)
        assert response.status == 200 and response.getheader("Content-Type") == "font/woff2", font


@pytest.mark.parametrize("path", ["/attempt/../../etc/passwd", "/attempt/..%2f..%2fetc%2fpasswd", "/attempt/none",
                                  "/attempt/", "/etc/passwd", "/style.css/../x", "/tasks/"])
def test_unknown_paths_and_sessions_are_not_found(running, path):
    assert _request(running, path, cookie=_login(running))[0].status == 404


def test_another_user_of_this_computer_is_refused(running, monkeypatch):
    """Other users can reach a port on 127.0.0.1; the owner of the client's socket is checked first."""
    from autorelabel import localweb

    monkeypatch.setattr(localweb, "same_user", lambda conn: False)
    response, body = _request(running, running.launch_url.split(str(running.port), 1)[1])
    assert response.status == 403 and "another user" in body
    assert not running.token_used                      # the launch address is still good for its owner


def test_the_owner_of_a_loopback_connection_is_found():
    """Against the real /proc/net/tcp: this process connected, so the client end is this uid."""
    import os
    import socket

    from autorelabel import localweb

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    client = socket.create_connection(listener.getsockname())
    conn, _ = listener.accept()
    try:
        assert localweb.peer_uid(conn) == os.getuid() and localweb.same_user(conn)
    finally:
        for s in (conn, client, listener):
            s.close()


def test_a_connection_from_another_uid_is_not_this_user(tmp_path):
    from autorelabel import localweb

    class Conn:
        def getpeername(self):
            return ("127.0.0.1", 40000)

        def getsockname(self):
            return ("127.0.0.1", 8080)

    peer, own = localweb._proc_address(("127.0.0.1", 40000)), localweb._proc_address(("127.0.0.1", 8080))
    table = tmp_path / "tcp"
    table.write_text("  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  inode\n"
                     f"   0: {own} 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000  0 1\n"
                     f"   1: {peer} {own} 01 00000000:00000000 00:00000000 00000000  1001  0 2\n")
    assert localweb.peer_uid(Conn(), table) == 1001                 # type: ignore[arg-type]
    assert localweb._proc_address(("127.0.0.1", 8080)) == "0100007F:1F90"
    assert not localweb.same_user(Conn(), tmp_path / "missing")      # type: ignore[arg-type]
