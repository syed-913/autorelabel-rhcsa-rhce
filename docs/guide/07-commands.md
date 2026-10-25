# Command reference

Everything you can do in the text interface is also available as a command, plus a few tools for troubleshooting and for people who write tasks. This page describes every command. You can always ask autorelabel itself, too:

```bash
./autorelabel --help              # every command
./autorelabel exam --help         # the commands under "exam"
./autorelabel exam start --help   # the options of one command
```

## How to run a command

Run commands from the repository folder: `./autorelabel <command> [options]`. The first command you ever run sets up the private Python environment, exactly as the interface does.

> **Can I run autorelabel from another folder?**
> Yes. The script finds its own folder, so a symbolic link in a folder on your `PATH` works:
>
> ```bash
> ln -s ~/autorelabel-rhcsa-rhce/autorelabel ~/.local/bin/autorelabel
> ```
>
> After that, `autorelabel doctor` works from anywhere. (Adjust the first path to where you cloned the repository.)

> **Can I use the interface and commands at the same time?**
> Yes, they work on the same session. A common setup is the exam screen in one terminal, `./autorelabel exam timer` in a small second one, and your SSH sessions in a third.

## Quick reference

| Command | What it does |
|---|---|
| `./autorelabel` | Open the text interface. |
| `./autorelabel rhcsa` / `rhce` | Open the interface and start a new exam. |
| `./autorelabel resume` | Open the interface at your current session. |
| `./autorelabel exam start <rhcsa\|rhce>` | Draw an exam, prepare the lab and start the clock. |
| `./autorelabel exam begin` | Start the clock of an exam prepared with `--no-start`. |
| `./autorelabel exam tasks` | Print the task sheet: your systems, the passwords and every task. |
| `./autorelabel exam status` | The session's state and the time left. |
| `./autorelabel exam timer` | The time left in large digits, for a spare terminal. |
| `./autorelabel ssh <node>` | Log in to a node over SSH. |
| `./autorelabel console <node>` | Attach to a node's serial console. |
| `./autorelabel node <action> <node>` | Power on, reset, or reset a node to the exam start. |
| `./autorelabel exam submit` | End the exam now and grade it. |
| `./autorelabel exam grade` | Grade the exam in this terminal. |
| `./autorelabel exam results` | Print the graded report. |
| `./autorelabel exam retake` | The same exam again, from its starting point. |
| `./autorelabel exam resume` | Restart an exam's lab after your computer restarted. |
| `./autorelabel exam abandon` | Give up the current session. |
| `./autorelabel doctor` | Check that this computer can run the labs. |
| `./autorelabel config` | Show or change settings. |
| `./autorelabel box build` / `box status` | Build the RHEL 10 box, or show its state. |
| `./autorelabel lab <up\|status\|health\|destroy>` | Manage the lab VMs directly. |
| `./autorelabel content download` | Download the RHCE content (once). |
| `./autorelabel report` | Write a problem report to post on the issue tracker. |
| `./autorelabel uninstall` | Remove everything autorelabel created. |
| `./autorelabel bank …` / `selftest` | Tools for people who write tasks. |
| `./autorelabel banner` | Print the banner. |

## Opening the text interface

```bash
./autorelabel          # the home screen
./autorelabel rhcsa    # straight to a new RHCSA exam (rhce for RHCE)
./autorelabel resume   # straight back to the current session
```

If a session is already open, `rhcsa` and `rhce` ask before replacing it.

## Taking an exam from the command line

A whole exam can run without the interface. A typical session looks like this:

```bash
./autorelabel exam start rhcsa          # draw an exam, prepare the lab, start the clock
./autorelabel exam tasks                # read the task sheet and the passwords
./autorelabel console node1             # task 1: node1 has no network yet
./autorelabel ssh node2                 # most other tasks
./autorelabel exam timer --compact      # in another terminal, to watch the time
./autorelabel exam submit               # when you are done (or let the time run out)
./autorelabel exam results --solutions  # your score, every check, every solution
```

### `exam start <rhcsa|rhce> [--seed N] [--no-start] [-v]`

Draws a new exam, prepares the lab (printing each stage) and starts the clock. Before an RHCE exam it downloads the RHCE content if that hasn't happened yet.

- `--no-start` prepares the lab without starting the clock. Start it later with `./autorelabel exam begin`.
- `--seed N` fixes the random draw. Two people using the same seed get the same tasks, provided their history leads to the same weighting (the draw favours objectives you haven't practised recently).
- `-v` shows the full output of the tools working underneath (Vagrant, the provisioning scripts).

If a session is still open, `exam start` refuses and tells you how to close it.

> **What happens to the old session if I abandon it?**
> It is closed without grading and stays out of your history. Its lab is replaced when the next exam is prepared.

### `exam begin`

Starts the clock of an exam prepared with `exam start --no-start`.

### `exam tasks`

Prints the task sheet: each node's name, full host name, address and root password, then every task with its points. For RHCE it also prints the `student` and `ansible` passwords, the Git repository, the VS Code address and the inventory groups. If difficulty display is on, each task shows its difficulty.

### `exam status`

Prints the session's ID, its state, the time left and whether the proctor is running. Like opening the interface, it also repairs what it can: it restarts the proctor if it stopped, and it locks the exam if the time ran out while nothing was running.

### `exam timer [--compact] [--once]`

Shows the time left, every second, until the exam ends or you press `Ctrl+C`. It turns yellow with 10 minutes left and red with 2 minutes left.

- No option: large digits, centred in the terminal.
- `--compact`: a single line, for a narrow terminal.
- `--once`: prints the time left once and exits, which suits a tmux or shell status line. For tmux, for example:

```bash
tmux set -g status-interval 1
tmux set -g status-right '#(~/autorelabel-rhcsa-rhce/autorelabel exam timer --once)'
```

### `ssh <node> [--user USER]`

Logs you in to a node over the lab network: as `root`, or as `student` on the RHCE `control` node. SSH asks for the account's password, which the instructions give (`./autorelabel exam tasks` prints them). `--user` picks another account, for example `--user ansible`. It is refused once the exam is locked.

> **Why does SSH to node1 fail at the start of an RHCSA exam?**
> Because node1 has no network yet: configuring it is your first task. Use `./autorelabel console node1` until then.

### `console <node>`

Attaches to the node's serial console, where you see GRUB, `rd.break` shells and emergency mode. It first prints how to log in (`root` and its password, when the instructions give one). Press Enter for a prompt and `Ctrl+]` to leave. It is refused once the exam is locked.

### `node <power-on|reset|reset-to-start> <node>`

- `power-on` starts a node that is shut off.
- `reset` is a hard reboot, like a reset button. Use it for a node that no longer responds.
- `reset-to-start` puts the node back exactly as it was when the exam started. **All your work on that node is lost**, the clock keeps running, and it is recorded as an incident in your results.

### `exam submit`

Ends the exam now: the lab is frozen and graded. If the proctor is running, it grades in the background (follow it with `./autorelabel exam status`). If it isn't, grading runs in your terminal.

### `exam grade`

Grades the exam in your terminal, showing each phase and each node's reboot. If the exam is still running, it is locked first, which ends it. The proctor normally grades by itself, so you only need it if grading was interrupted and you prefer the command line to the interface. It exits with 0 for a pass and 3 for a fail.

### `exam results [session] [--solutions]`

Prints the graded report of the current session, or of the session you name (the session IDs are the folder names in `.workspace/sessions/`). `--solutions` adds every task's solution after the report.

### `exam retake`

Prepares the same exam again (same tasks, same details) from its starting point. Start the clock with `./autorelabel exam begin`.

### `exam resume`

Starts the lab of an exam that was interrupted by a restart of your computer, and continues the clock. The time your computer was off isn't counted, unless you turned off *Forgive host downtime*.

> **What is the difference between `exam resume` and `./autorelabel resume`?**
> `exam resume` brings an interrupted exam back from the command line. `./autorelabel resume` opens the text interface at your current session, whatever state it is in, and offers the right next step there.

### `exam abandon`

Gives up the current session. It isn't graded and isn't added to your history.

## Checking your computer

### `doctor [--exam rhcsa|rhce] [--json]`

Runs every host check and prints ✔, `!` or ✘ for each, with the exact commands for your distribution under anything that needs fixing. It never changes anything itself. It exits with 1 when something must be fixed.

- `--exam rhce` checks free memory against the RHCE lab, which needs more.
- `--json` prints the checks as JSON, for scripts.

Every check is explained in [Troubleshooting](09-troubleshooting.md#the-doctors-checks).

## Settings

### `config [key=value ...]`

Without arguments, prints all settings as JSON. With arguments, changes them first:

```bash
./autorelabel config scoring=strict show_difficulty_during_exam=true
./autorelabel config warnings_minutes=45,15,5
```

Lists are comma-separated, and true/false settings accept `true`, `false`, `yes`, `no`, `on`, `off`, `1` and `0`. An unknown key, or a provider, profile or scoring value that doesn't exist, is refused with exit code 2. Every key is described in [Settings](08-settings.md).

## The box and the lab

### `box build [--provider libvirt|virtualbox] [-v]`

Builds the RHEL 10 box from your ISO, for the configured hypervisor unless you name one. It takes about 10 to 15 minutes. `-v` shows Packer's full output.

### `box status`

Shows, for each hypervisor, whether a box is ready and when it was built.

### `lab up <rhcsa|rhce> [-v]`, `lab status`, `lab health`, `lab destroy`

These manage the lab VMs directly. Exams create and reset the lab by themselves, so you normally never need them; they are for troubleshooting and development.

- `lab up` creates and sets up the lab without any exam tasks.
- `lab status [exam]` prints each VM's power state and its management and lab addresses.
- `lab health [exam]` checks the lab's services and prints any problem.
- `lab destroy [exam]` deletes the lab VMs and their snapshots. The box, the networks and the storage pool are kept.

## RHCE content

### `content download [-v] [--no-code-server]`

Downloads `ansible-navigator`, the `ansible.posix` and `community.general` collections and code-server with its extensions, at the pinned versions, into the lab storage. The first RHCE exam does this automatically. `--no-code-server` skips VS Code in the browser.

## Problem reports

### `report ["what went wrong"] [--log FILE] [--exam rhcsa|rhce]`

Writes a problem report on demand: what went wrong in your words, the versions of autorelabel and every tool, the doctor's checks and the end of the log. Your home folder, user name and host name are replaced and passwords are masked. It prints the file's location and the issue tracker's address. `--log` includes a specific log, and `--exam` adds that exam's details. See [Troubleshooting](09-troubleshooting.md#problem-reports).

## Removing everything

### `uninstall [--dry-run] [--yes] [--keep-box] [--delete-iso]`

Removes everything autorelabel created on this computer. This command is plain bash, so it works even when the Python environment is broken.

- `--dry-run` lists what would be removed, and removes nothing.
- `--yes` doesn't ask for confirmation.
- `--keep-box` keeps the RHEL 10 box, so a later reinstall skips the box build.
- `--delete-iso` also deletes your RHEL 10 ISO, which is otherwise kept.

See [Files and uninstalling](10-files-and-uninstall.md).

## Tools for writing tasks

These are for people who add or change tasks in the bank. [TASK-AUTHORING.md](../TASK-AUTHORING.md) explains them in depth.

| Command | What it does |
|---|---|
| `bank lint [rhcsa] [rhce] [--gate none\|wave1\|full] [--warnings]` | Checks every task's format and traceability, and the coverage rule. |
| `bank coverage <rhcsa\|rhce> [--write\|--check]` | Prints the coverage report; `--write` updates `docs/COVERAGE-*.md` and the [objectives page](12-objectives.md), `--check` fails if they are out of date. |
| `bank sample <rhcsa\|rhce> [--seed N] [--json]` | Prints the exam a seed would draw, without preparing anything. |
| `selftest [tasks…] [--exam rhcsa\|rhce] [--changed] [--sweep]` | Runs tasks on real VMs: setup, reference solution, accepted alternatives and classic mistakes. |

> **Is `selftest` safe to run while I am practising?**
> No. It uses the same lab, rebuilding it and running many tasks one after another, and it takes a long time. Run it only when you aren't using autorelabel for an exam or practice.

## Other options

| Option | What it does |
|---|---|
| `--help` | Help for autorelabel or for any command. |
| `--version` | Prints the version. |
| `--debug` | Writes debug details to the log and shows full error tracebacks. Put it before the command: `./autorelabel --debug doctor`. |

## Environment variables

| Variable | What it does |
|---|---|
| `AUTORELABEL_WORKSPACE` | Uses another folder for settings, sessions and logs (the default is `.workspace/` in the repository). This keeps a second, separate setup, for example one per hypervisor. |
| `AUTORELABEL_PYTHON` | The Python used to create the private environment, for example `python3.12`. |
| `AUTORELABEL_DEBUG` | When set (to `1`), the box build also writes Packer's detailed log. |
| `NO_COLOR` | When set, output has no colours. |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (for `exam grade`: you passed). |
| 1 | Something failed, or the doctor found something to fix. |
| 2 | Invalid usage, such as an unknown setting. |
| 3 | `exam grade`: the exam was graded and you didn't pass. |
| 130 | Interrupted with `Ctrl+C`. |
