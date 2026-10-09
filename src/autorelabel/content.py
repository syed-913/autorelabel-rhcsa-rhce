"""One-time RHCE content download, done on the host (the only step that needs
internet). Everything else in the RHCE lab is offline:

  wheels/       ansible-navigator + ansible-runner and dependencies (cp312, manylinux)
  collections/  ansible.posix, community.general (versions compatible with the DVD's ansible-core)
  code-server/  code-server RPM and the Red Hat Ansible extension (.vsix) from Open VSX

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
ANSIBLE_CORE_VERSION = (2, 16, 14)       # what the RHEL 10.0 DVD ships
COLLECTIONS = ["ansible.posix", "community.general"]
PIP_PACKAGES = ["ansible-navigator", "ansible-runner"]
LineFn = Callable[[str], None]


class ContentError(RuntimeError):
    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint


def content_dir(settings: Settings) -> Path:
    return box.storage_layout(settings)["content"]


def manifest_path(settings: Settings) -> Path:
    return content_dir(settings) / "manifest.json"


def status(settings: Settings) -> tuple[bool, str]:
    m = read_json(manifest_path(settings), default=None)
    if not m:
        return False, "not downloaded yet (needs internet once)"
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


def _collection(fqcn: str, dest: Path, line: LineFn) -> str:
    ns, name = fqcn.split(".")
    base = f"https://galaxy.ansible.com/api/v3/plugin/ansible/content/published/collections/index/{ns}/{name}"
    data = _get_json(f"{base}/versions/?limit=40")
    candidates = sorted(data.get("data", []), key=lambda v: _ver(v["version"]), reverse=True)
    for v in candidates:
        if re.search(r"[a-z]", v["version"]):       # skip pre-releases
            continue
        detail = _get_json(f"{base}/versions/{v['version']}/")
        if _requires_ok(detail.get("requires_ansible")):
            fname = f"{ns}-{name}-{v['version']}.tar.gz"
            _download(detail["download_url"], dest / fname, line)
            return fname
    raise ContentError(f"no {fqcn} release compatible with ansible-core 2.16 found on Galaxy")


def download(settings: Settings, *, on_line: LineFn | None = None, on_step: LineFn | None = None,
             with_code_server: bool = True) -> Path:
    line = on_line or (lambda s: None)
    step = on_step or (lambda s: None)
    root = content_dir(settings)
    for sub in ("wheels", "collections", "code-server"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    step("Downloading ansible-navigator (Python wheels for the control node)")
    res = proc.stream([sys.executable, "-m", "pip", "download", "--disable-pip-version-check", "--no-cache-dir",
                       "--dest", str(root / "wheels"), "--only-binary=:all:", "--python-version", "3.12",
                       "--implementation", "cp", "--platform", "manylinux_2_28_x86_64",
                       "--platform", "manylinux_2_17_x86_64", "--platform", "manylinux2014_x86_64",
                       *PIP_PACKAGES], on_line=line, timeout=1800, env=paths.tool_env())
    if not res.ok:
        raise ContentError("pip download failed", "Check your internet connection (pypi.org) and retry.")

    step("Downloading Ansible collections from Galaxy")
    for fqcn in COLLECTIONS:
        try:
            fname = _collection(fqcn, root / "collections", line)
        except OSError as exc:
            raise ContentError(f"Galaxy download failed for {fqcn}: {exc}",
                               "Check your internet connection (galaxy.ansible.com) and retry.") from exc
        line(f"  {fname}")

    if with_code_server:
        step("Downloading code-server and the Red Hat Ansible extension")
        try:
            rel = _get_json("https://api.github.com/repos/coder/code-server/releases/latest")
            asset = next(a for a in rel["assets"] if re.fullmatch(r"code-server-[\d.]+-amd64\.rpm", a["name"]))
            _download(asset["browser_download_url"], root / "code-server" / asset["name"], line)
            ext = _get_json("https://open-vsx.org/api/redhat/ansible/latest")
            _download(ext["files"]["download"], root / "code-server" / f"redhat.ansible-{ext['version']}.vsix", line)
        except (OSError, StopIteration, KeyError) as exc:
            raise ContentError(f"code-server download failed: {exc}",
                               "Check your internet connection (github.com, open-vsx.org), or turn code-server "
                               "off in Settings.") from exc

    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "manifest.json" and not p.name.endswith(".part"):
            files[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    atomic_write_json(manifest_path(settings), {"date": time.strftime("%Y-%m-%d"), "files": files,
                                                "ansible_core": ".".join(map(str, ANSIBLE_CORE_VERSION))})
    return root
