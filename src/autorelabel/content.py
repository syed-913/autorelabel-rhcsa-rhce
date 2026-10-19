"""One-time RHCE content download, done on the host (the only step that needs
internet). Everything else in the RHCE lab is offline:

  wheels/       ansible-navigator + ansible-runner and dependencies (cp312, manylinux)
  collections/  ansible.posix, community.general (versions compatible with the DVD's ansible-core)
  code-server/  code-server RPM, the Red Hat Ansible extension and its dependencies (Open VSX)

All versions are pinned (below, and vagrant/content/rhce-wheels.txt for the wheels).

The execution-environment / development-container image is built inside the lab from
the RHEL 10 DVD's own packages plus these wheels, so no registry login is ever needed.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import box, paths, proc
from .config import Settings
from .fsutil import atomic_write_json, read_json

UA = {"User-Agent": "autorelabel (RHCE lab content download)"}
# Every version is pinned: the RHCE self-test verified the tasks against exactly these, so a
# new upstream release can't change the lab under the tasks. Update them together, then self-test.
ANSIBLE_CORE_VERSION = (2, 16, 14)       # what the RHEL 10.0 DVD ships
COLLECTIONS = {"ansible.posix": "2.2.2", "community.general": "11.4.9"}
PIP_PACKAGES = ["ansible-navigator", "ansible-runner"]
WHEEL_PINS = paths.VAGRANT_DIR / "content" / "rhce-wheels.txt"   # every wheel, exact versions
CODE_SERVER_VERSION = "4.141.0"
# The Ansible extension and everything it depends on. 26.3.0 and later also depend on
# ms-python.vscode-python-envs, which needs a native helper that Open VSX builds don't ship:
# it never finishes activating, and the Ansible extension waits for it forever.
EXTENSIONS = {"redhat.ansible": "26.1.3", "ms-python.python": "2026.4.0",
              "redhat.vscode-yaml": "2.1.2026101708"}
OPEN_VSX = "https://open-vsx.org/api"
LineFn = Callable[[str], None]


class ContentError(RuntimeError):
    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint


def content_dir(settings: Settings) -> Path:
    return box.storage_layout(settings)["content"]


def manifest_path(settings: Settings) -> Path:
    return content_dir(settings) / "manifest.json"


def pins_digest() -> str:
    """Changes whenever a pinned version does: older downloads are then out of date."""
    h = hashlib.sha256(WHEEL_PINS.read_bytes())
    h.update(json.dumps([COLLECTIONS, EXTENSIONS, CODE_SERVER_VERSION], sort_keys=True).encode())
    return h.hexdigest()[:16]


def status(settings: Settings) -> tuple[bool, str]:
    m = read_json(manifest_path(settings), default=None)
    if not m:
        return False, "not downloaded yet (needs internet once)"
    if m.get("pins") != pins_digest():
        return False, "the pinned versions changed; download again"
    missing = [f for f in m.get("files", {}) if not (content_dir(settings) / f).exists()]
    if missing:
        return False, f"{len(missing)} file(s) missing; download again"
    return True, f"downloaded {m.get('date', '?')}"


def _get(url: str, timeout: float = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _get_json(url: str) -> Any:
    return json.loads(_get(url).decode())


def _download(url: str, dest: Path, line: LineFn) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    line(f"downloading {url}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as fh:
        shutil.copyfileobj(r, fh, 1024 * 1024)
    tmp.replace(dest)


def _ver(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text)[:3])


def _requires_ok(spec: str | None) -> bool:
    """Evaluate a collection's requires_ansible (e.g. '>=2.15.0,<2.19') against our ansible-core."""
    if not spec:
        return True
    for part in spec.split(","):
        part = part.strip()
        m = re.match(r"(>=|<=|==|!=|>|<)\s*([\d.]+)", part)
        if not m:
            continue
        op, v = m.group(1), _ver(m.group(2))
        cur = ANSIBLE_CORE_VERSION[: len(v)]
        ok = {">=": cur >= v, "<=": cur <= v, "==": cur == v, "!=": cur != v, ">": cur > v, "<": cur < v}[op]
        if not ok:
            return False
    return True


def _collection(fqcn: str, version: str, dest: Path, line: LineFn) -> str:
    ns, name = fqcn.split(".")
    base = f"https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/{ns}/{name}"
    detail = _get_json(f"{base}/versions/{version}/")
    if not _requires_ok(detail.get("requires_ansible")):
        raise ContentError(f"{fqcn} {version} does not support ansible-core "
                           f"{'.'.join(map(str, ANSIBLE_CORE_VERSION))}")
    fname = f"{ns}-{name}-{version}.tar.gz"
    _download(detail["download_url"], dest / fname, line)
    return fname


def _open_vsx(ident: str, version: str) -> dict[str, Any]:
    ns, name = ident.split(".", 1)
    d = _get_json(f"{OPEN_VSX}/{ns}/{name}/{version}")
    if d.get("targetPlatform") not in (None, "universal", "linux-x64"):
        d = _get_json(f"{OPEN_VSX}/{ns}/{name}/linux-x64/{version}")
    return d


def _extensions(dest: Path, line: LineFn) -> list[str]:
    """Download EXTENSIONS, following their dependencies (code-server can't fetch them offline,
    and an extension whose dependencies are missing never activates); a dependency without a
    pinned version is an error. Writes extensions.txt: the files in install order, dependencies first."""
    order: list[str] = []
    seen: set[str] = set()

    def visit(ident: str) -> None:
        if ident in seen:
            return
        seen.add(ident)
        if ident not in EXTENSIONS:
            raise ContentError(f"the editor extension {ident} is needed but has no pinned version",
                               "Add it to EXTENSIONS in src/autorelabel/content.py.")
        d = _open_vsx(ident, EXTENSIONS[ident])
        for dep in d.get("dependencies") or []:
            visit(f"{dep['namespace']}.{dep['extension']}")
        fname = f"{ident}-{d['version']}.vsix"
        _download(d["files"]["download"], dest / fname, line)
        order.append(fname)

    visit("redhat.ansible")
    for old in dest.glob("*.vsix"):          # earlier versions
        if old.name not in order:
            old.unlink()
    (dest / "extensions.txt").write_text("".join(f"{f}\n" for f in order))
    return order


def download(settings: Settings, *, on_line: LineFn | None = None, on_step: LineFn | None = None,
             with_code_server: bool = True) -> Path:
    line = on_line or (lambda s: None)
    step = on_step or (lambda s: None)
    root = content_dir(settings)
    for sub in ("wheels", "collections", "code-server"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    step("Downloading ansible-navigator (Python wheels for the control node)")
    (root / "constraints.txt").unlink(missing_ok=True)       # written by older versions
    res = proc.stream([sys.executable, "-m", "pip", "download", "--disable-pip-version-check", "--no-cache-dir",
                       "--dest", str(root / "wheels"), "--only-binary=:all:", "--python-version", "3.12",
                       "--implementation", "cp", "--platform", "manylinux_2_28_x86_64",
                       "--platform", "manylinux_2_17_x86_64", "--platform", "manylinux2014_x86_64",
                       "-c", str(WHEEL_PINS), *PIP_PACKAGES], on_line=line, timeout=1800, env=paths.tool_env())
    if not res.ok:
        raise ContentError("pip download failed", "Check your internet connection (pypi.org) and retry.")
    pinned = {ln.strip().lower() for ln in WHEEL_PINS.read_text().splitlines() if "==" in ln}
    for whl in (root / "wheels").glob("*.whl"):           # versions from earlier downloads
        name, version = whl.name.split("-")[:2]
        if f"{name.lower().replace('_', '-')}=={version}" not in pinned:
            whl.unlink()

    step("Downloading Ansible collections from Galaxy")
    keep = {f"{fqcn.replace('.', '-')}-{v}.tar.gz" for fqcn, v in COLLECTIONS.items()}
    for old in (root / "collections").glob("*.tar.gz"):
        if old.name not in keep:
            old.unlink()
    for fqcn, version in COLLECTIONS.items():
        try:
            fname = _collection(fqcn, version, root / "collections", line)
        except OSError as exc:
            raise ContentError(f"Galaxy download failed for {fqcn}: {exc}",
                               "Check your internet connection (galaxy.ansible.com) and retry.") from exc
        line(f"  {fname}")

    if with_code_server:
        step("Downloading code-server and the Red Hat Ansible extension (with its dependencies)")
        try:
            rpm = f"code-server-{CODE_SERVER_VERSION}-amd64.rpm"
            _download(f"https://github.com/coder/code-server/releases/download/v{CODE_SERVER_VERSION}/{rpm}",
                      root / "code-server" / rpm, line)
            for old in (root / "code-server").glob("code-server-*.rpm"):     # earlier releases
                if old.name != rpm:
                    old.unlink()
            for f in _extensions(root / "code-server", line):
                line(f"  {f}")
        except (OSError, KeyError) as exc:
            raise ContentError(f"code-server download failed: {exc}",
                               "Check your internet connection (github.com, open-vsx.org), or turn code-server "
                               "off in Settings.") from exc

    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "manifest.json" and not p.name.endswith(".part"):
            files[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    atomic_write_json(manifest_path(settings), {"date": time.strftime("%Y-%m-%d"), "files": files,
                                                "ansible_core": ".".join(map(str, ANSIBLE_CORE_VERSION)),
                                                "pins": pins_digest()})
    return root
