"""The script wrapper used for every setup, solution and check, exercised with a local bash."""

from __future__ import annotations

import subprocess

from autorelabel import grader, paths, remote


def run_wrapped(script: str, env: dict[str, str] | None = None, lib: str = "") -> subprocess.CompletedProcess:
    # Same transport as on the VMs: the wrapped script arrives on bash's stdin.
    return subprocess.run(["bash", "-s"], input=remote._wrap(lib + script, env), capture_output=True,
                          text=True, timeout=60, env={"PATH": "/usr/bin:/bin", "SUDO_USER": "vagrant"})


def test_commands_cannot_swallow_the_rest_of_the_script():
    r = run_wrapped("cat >/dev/null\necho still-here\n")
    assert r.stdout.strip() == "still-here"


def test_root_shell_environment():
    r = run_wrapped('echo "$PATH"; echo "sudo=${SUDO_USER:-none}"; echo "$P_X"\n', env={"P_X": "a b'c"})
    path, sudo, value = r.stdout.splitlines()
    assert path.split(":")[:2] == ["/usr/local/sbin", "/usr/local/bin"]
    assert sudo == "sudo=none"
    assert value == "a b'c"


def test_quiet_grep_survives_pipefail_and_still_fails_when_it_should():
    lib = (paths.BANKS / "lib" / "check-lib.sh").read_text()
    ok = run_wrapped("set -e\nseq 1 300000 | grep -q '^1$'\necho matched\n", lib=lib)
    assert ok.returncode == 0 and ok.stdout.strip() == "matched"
    miss = run_wrapped("set -e\nseq 1 10 | grep -q '^42$'\necho not-reached\n", lib=lib)
    assert miss.returncode != 0 and "not-reached" not in miss.stdout
    files = run_wrapped("set -e\ngrep -q root /etc/passwd\necho file-ok\n", lib=lib)
    assert files.stdout.strip() == "file-ok"


def test_check_exit_codes():
    lib = (paths.BANKS / "lib" / "check-lib.sh").read_text()
    assert run_wrapped(grader.check_script(lib, "true")).returncode == 0
    failing = run_wrapped(grader.check_script(lib, "false\necho not-reached"))
    assert failing.returncode == 1 and "not-reached" not in failing.stdout
    # a check's own ssh failing (rc 255) must not look like the node being unreachable
    assert run_wrapped(grader.check_script(lib, "(exit 255)")).returncode == 1
    assert run_wrapped(grader.check_script(lib, "exit 3")).returncode == 3
