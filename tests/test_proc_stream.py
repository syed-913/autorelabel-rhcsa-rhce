"""proc.stream splits output the way a terminal shows it: progress counters redraw one line."""

from __future__ import annotations

from autorelabel import proc

# vagrant-libvirt's box upload: "\r" + erase-line before every value, the next message drawn over it
VAGRANT = r"printf 'Uploading...\n\r\e[KProgress: 0%%\r\e[KProgress: 0%%\r\e[KProgress: 100%%\r\e[K==> Creating\n'"


def test_progress_counters_are_redraws_not_lines(tmp_path):
    got: list[str] = []
    log_file = tmp_path / "op.log"
    res = proc.stream(["bash", "-c", VAGRANT], on_line=got.append, log_file=log_file)
    assert res.ok
    assert got == ["Uploading...", "Progress: 0%", "Progress: 100%", "==> Creating"]
    assert [type(g) for g in got] == [str, proc.Progress, proc.Progress, str]
    # the log and the result keep the counter's last value only, without escape codes
    assert res.out == "Uploading...\nProgress: 100%\n==> Creating"
    assert log_file.read_text().splitlines()[1:4] == ["Uploading...", "Progress: 100%", "==> Creating"]


def test_crlf_split_across_reads_is_one_line_break():
    got: list[str] = []
    lines = proc._Lines(got.append, lambda _s: None)
    lines.feed("first\r")
    lines.feed("\nsecond\n")
    lines.feed("", final=True)
    assert got == ["first", "second"]
    assert all(type(g) is str for g in got)


def test_the_latest_value_shows_while_the_tool_is_quiet():
    got: list[str] = []
    lines = proc._Lines(got.append, lambda _s: None)
    lines.feed("\rProgress: 93%\rProgress: 94%")     # 94% has no terminator yet
    assert got == ["Progress: 93%"]
    lines.feed("", idle=True)
    assert got == ["Progress: 93%", "Progress: 94%"]


def test_input_and_exit_code_still_work():
    res = proc.stream(["bash", "-c", "cat; echo oops >&2; exit 3"], input="in1\nin2\n")
    assert res.rc == 3 and res.out == "in1\nin2\noops"
