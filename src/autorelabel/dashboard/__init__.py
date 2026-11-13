"""The results dashboard: a read-only view of the graded attempts, served on 127.0.0.1."""

from __future__ import annotations

import shutil
import subprocess
import threading

_running: list = []          # the dashboard the text interface started, at most one


def open_in_browser(url: str) -> bool:
    """Open `url` in the desktop's browser without letting the opener write to this terminal
    (a full-screen text interface may be drawing in it). False when there is no opener."""
    opener = shutil.which("xdg-open")
    if opener:
        try:
            subprocess.Popen([opener, url], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            return True
        except OSError:
            pass
    try:
        import webbrowser

        return webbrowser.open(url)
    except Exception:
        return False


def start_in_background():
    """A dashboard served from a thread of this process (the text interface), for as long as the
    process runs. Each call replaces the previous one, because a launch address works once."""
    from .server import Dashboard

    while _running:
        old = _running.pop()
        old.shutdown()
        old.server_close()
    srv = Dashboard()
    threading.Thread(target=srv.serve_forever, name="results-dashboard", daemon=True).start()
    _running.append(srv)
    return srv
