"""The dashboard's HTTP server: 127.0.0.1 only, read-only, and closed to everything but the
browser tab it was opened for.

"Only local" is not a boundary by itself. Any web page can make the browser send requests to
127.0.0.1, other users of this computer can connect to the port, and a public name can be made
to resolve to 127.0.0.1 (DNS rebinding). So every request is checked, in this order:

1. Host must be 127.0.0.1:<port> or localhost:<port> (rebinding sends the attacker's name).
2. GET or HEAD only: nothing here changes anything.
3. A token made at launch, known only to whoever saw the launch address. The first request
   carries it in the path and is answered with a cookie (HttpOnly, SameSite=Strict) and a
   redirect, so the token does not stay in the address bar; every other request needs the cookie.
4. Routes are a fixed table. No file is ever served by a name taken from the request.

Every response forbids scripts, frames and remote content (Content-Security-Policy), and the
pages contain no script to begin with.
"""

from __future__ import annotations

import hmac
import secrets
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .. import stats
from ..bank import cached_bank
from . import pages

HOST = "127.0.0.1"
COOKIE = "autorelabel_dashboard"
HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; "
                               "base-uri 'none'; form-action 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def bank_names(exam: str) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]], dict[str, str]]:
    """objective id -> (text, domain title); task id -> (title, domain title); domain id -> title."""
    bank = cached_bank(exam)
    domains = {d.id: d.title for d in bank.objectives.domains}
    objectives = {o.id: (o.text, d.title) for d in bank.objectives.domains for o in d.objectives}
    titles = {t.id: (t.title, domains.get(t.domain, t.domain)) for t in bank.tasks.values()}
    return objectives, titles, domains


class Dashboard(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, port: int = 0):
        super().__init__((HOST, port), Handler)
        self.token = secrets.token_urlsafe(32)        # in the launch address, used once
        self.cookie = secrets.token_urlsafe(32)       # what the browser holds afterwards
        self.token_used = False

    @property
    def port(self) -> int:
        return int(self.server_address[1])

    @property
    def launch_url(self) -> str:
        return f"http://{HOST}:{self.port}/open/{self.token}"


class Handler(BaseHTTPRequestHandler):
    server: Dashboard
    server_version = "autorelabel"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return                                                    # no request log: nothing to keep

    # --- answers ----------------------------------------------------------------------------------
    def _send(self, status: int, body: str = "", content_type: str = "text/html; charset=utf-8",
              extra: dict[str, str] | None = None) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        for name, value in {**HEADERS, **(extra or {})}.items():
            self.send_header(name, value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _refuse(self, status: HTTPStatus, why: str) -> None:
        self._send(status, f"{status.value} {why}\n", "text/plain; charset=utf-8")

    # --- checks -----------------------------------------------------------------------------------
    def _host_ok(self) -> bool:
        return self.headers.get("Host", "") in (f"{HOST}:{self.server.port}", f"localhost:{self.server.port}")

    def _cookie_ok(self) -> bool:
        try:
            jar = SimpleCookie(self.headers.get("Cookie", ""))
        except Exception:                 # a malformed Cookie header is simply no cookie
            return False
        got = jar[COOKIE].value if COOKIE in jar else ""
        return hmac.compare_digest(got.encode(), self.server.cookie.encode())

    # --- requests ---------------------------------------------------------------------------------
    def do_GET(self) -> None:
        if not self._host_ok():
            return self._refuse(HTTPStatus.MISDIRECTED_REQUEST, "this server only answers as 127.0.0.1")
        url = urlsplit(self.path)
        path = url.path
        if path.startswith("/open/"):
            given = path.removeprefix("/open/")
            fresh = not self.server.token_used and hmac.compare_digest(given.encode(), self.server.token.encode())
            if not fresh and not self._cookie_ok():
                return self._refuse(HTTPStatus.FORBIDDEN, "this address has been used; start the dashboard again")
            self.server.token_used = True
            return self._send(HTTPStatus.SEE_OTHER, "", extra={
                "Location": "/", "Set-Cookie": f"{COOKIE}={self.server.cookie}; HttpOnly; SameSite=Strict; Path=/"})
        if not self._cookie_ok():
            return self._refuse(HTTPStatus.FORBIDDEN, "open the address the dashboard command printed")
        if path == "/style.css":
            return self._send(HTTPStatus.OK, pages.STYLE, "text/css; charset=utf-8")
        query = parse_qs(url.query)
        exam = query.get("exam", ["rhcsa"])[0]
        exam = exam if exam in pages.EXAMS else "rhcsa"
        exams_only = query.get("only", [""])[0] == "exams"
        try:
            if path.startswith("/attempt/"):
                results = stats.session_results(path.removeprefix("/attempt/"))
                if not results:
                    return self._refuse(HTTPStatus.NOT_FOUND, "no such attempt, or its results are gone")
                names = bank_names(results["exam"] if results.get("exam") in pages.EXAMS else "rhcsa")
                return self._send(HTTPStatus.OK, pages.attempt_page(results, names[2]))
            if path not in ("/", "/objectives", "/tasks"):
                return self._refuse(HTTPStatus.NOT_FOUND, "no such page")
            history = stats.load()
            objectives, titles, _domains = bank_names(exam)
            if path == "/":
                body = pages.overview(history, exam, exams_only, objectives, titles)
            elif path == "/objectives":
                body = pages.objectives_page(history, exam, exams_only, objectives)
            else:
                body = pages.tasks_page(history, exam, exams_only, titles)
            return self._send(HTTPStatus.OK, body)
        except Exception as exc:          # a page that cannot be built must not take the server down
            return self._refuse(HTTPStatus.INTERNAL_SERVER_ERROR,
                                f"this page could not be built ({type(exc).__name__})")

    do_HEAD = do_GET

    def _not_allowed(self) -> None:
        self._send(HTTPStatus.METHOD_NOT_ALLOWED, "405 read-only\n", "text/plain; charset=utf-8",
                   {"Allow": "GET, HEAD", "Connection": "close"})
        self.close_connection = True

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _not_allowed
