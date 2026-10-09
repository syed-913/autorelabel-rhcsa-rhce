# Writing tasks

Every task in `banks/<exam>/tasks/<domain>/<name>/` is a small, self-tested unit: a prompt in exam
style, the setup that creates its starting point, checks that grade it after a reboot, a
reference solution, and tests that prove the checks accept valid answers and catch classic
mistakes. A task ships only when `./autorelabel bank lint` is clean and `./autorelabel selftest`
passes on real VMs.

## Layout

```text
banks/rhcsa/tasks/storage/lvm-create/
├── task.yaml                 metadata, prompt, requirements, checks
├── setup.sh                  starting point, on the task's node (optional)
├── setup@utility.sh          ... or on another VM, one file per VM
├── solution.sh               reference solution (self-test); same naming as setup
├── solution.md               explanation shown after grading
└── tests/
    ├── alt-<name>.sh         a different valid answer: must score full marks
    ├── alt-<name>@node2.sh   ... the node2 part of the same alternative
    └── mistake-<name>.sh     a classic error: must NOT score full marks
```

`<script>.sh` runs on the task's `node`; `<script>@<vm>.sh` runs on that VM. Never create both
`setup.sh` and `setup@<task node>.sh`: they target the same node and only one would run (lint
rejects it). In RHCE banks a script can also target an inventory group: `setup@all.sh`,
`setup@prod.sh` run on every host of that group in the current lab profile.

## task.yaml

```yaml
title: Create LVM storage with a specific extent size
primary: rhcsa.storage.lv            # the objective this task is "about"
objectives: [rhcsa.storage.lv, rhcsa.storage.vg, ...]   # everything it exercises
facets:                              # objective:facet pairs (see objectives.yaml)
  - rhcsa.storage.lv:lv-create-extents
difficulty: hard                     # easy | medium | hard (rubric in the plan, §12.2)
difficulty_reason: >                 # why it meets the rubric
  A dependency chain where every value is exact ...
estimated_minutes: 12
node: node1                          # where the candidate mainly works
exclusive: [disk-node1]              # never two tasks with the same tag in one exam
resources:
  disk: {node1.disk1: 1100}          # MiB used on a lab disk (exam disk budget)
anchor: repos                        # only for the blueprint's anchor tasks
breaks_boot: false                   # setup leaves the node unbootable (fixed on the console)
console_only: false                  # node has no network at the start
practice_only: false                 # valid drill, never drawn into a full exam
params:
  vg: {choice: [datavg, appvg]}      # choice | range [lo, hi] | token <length> | value <x> | pool <name>
  user: {pool: usernames}            # pools (banks/<exam>/pools.yaml) are drawn without replacement
prompt: |
  On node1, create ... `{{vg}}` ... `{{lab.node1.disk1}}`
requirements:
  R1: "VG {{vg}} exists with {{pe}} MiB extents"
checks:
  - id: vg
    covers: [R1]                     # every requirement needs at least one check
    on: node1                        # default: the task's node; RHCE: "@group" too
    desc: "{{vg}}: extent size {{pe}} MiB"
    weight: 1                        # share of the task's points (partial credit)
    timeout: 60
    run: |
      test "$(vgs --noheadings --units m -o vg_extent_size {{vg}} | tr -d ' ')" = "{{pe}}.00m"
references:
  - "RHEL 10: Configuring and managing logical volumes > ..."
  - "man vgcreate(8)"
```

`mistakes_na: <reason>` replaces the mistake tests when no realistic mistake exists.

### Placeholders

- `{{name}}` (no spaces) is an autorelabel placeholder: a parameter, `{{param.field}}` for dict
  parameters, `{{pkgs.0}}` for list items, or a lab fact such as `{{lab.node1.ip}}`,
  `{{lab.repo_baseos}}`, `{{lab.groups.prod}}`, `{{lab.project_dir}}`. An unknown placeholder is a
  lint error, checked against both lab profiles.
- `{{ name }}` (with spaces) is left untouched, so prompts and `solution.md` can show Ansible and
  Jinja2 code verbatim. `{{ {{var}} }}` renders as `{{ env_name }}` when `var` is `env_name`.
- `lab.inventory_md` renders the RHCE inventory groups as a Markdown list.

Scripts get the same values as environment variables: `P_<NAME>` (`P_CASE_DESC` for dict
fields, `P_PKGS` and `P_PKGS_0`… for lists) and `LAB_<PATH>` (`LAB_NODE1_IP`,
`LAB_GROUPS_PROD`), plus `AR_NODE`, `AR_TASK` and, in RHCE, `AR_STUDENT_PASSWORD` and
`AR_ANSIBLE_PASSWORD`.

## Scripts (setup, solution, tests)

They run as root over SSH, like a root login shell: root's normal `PATH` (including
`/usr/local/bin`), no `SUDO_*` variables, stdin is `/dev/null`, and `banks/lib/setup-lib.sh` is
prepended, which sets `set -Eeuo pipefail` and an ERR trap. **Any failing command fails the
script**: append `|| true` where failure is expected (`find /` over `/proc`, `grep` over a glob
that may match nothing), and avoid `cmd | grep -q` in scripts (see below).

Helpers from `setup-lib.sh`:

| Helper | Use |
|---|---|
| `ar_install pkg...` | quiet `dnf install` |
| `ar_new_partition <disk> <MiB> [linux\|lvm\|swap]` | next free partition, prints its device |
| `ar_user <name> <password> [useradd args]` | create or reset a user |
| `ar_write <path> <mode>` | file from stdin |
| `ar_ssh_copy_id <user> <user@host> <password>` | what a candidate does with ssh-copy-id |
| `ar_gen_tree`, `ar_gen_tar`, `ar_tree_digest` | identical test data on every node, so one node can verify another's copy |
| `ar_lab_nic` | the lab interface name |
| `as_user <user> cmd...` | run as a user with a clean environment (never `sudo -u`: `flatpak --user` refuses it) |
| `as_student cmd...`, `student_sh '...'`, `student_write <path> [mode]` | RHCE: act as the candidate in `~/ansible` |

Reference solutions show *one* good way to do the task. Use `tests/alt-*.sh` for other valid
ways (a YAML inventory instead of INI, `semanage` vs a system role). Mistake tests reproduce one
classic error each; the first line comment says which.

Tasks whose setup leaves the node unbootable (`breaks_boot: true`) are solved by typing the
solution on the serial console in the self-test; keep those scripts to plain commands.

## Checks

Checks run **after the grading reboot**, read-only, with `set -e` and `pipefail`, and with
`banks/lib/check-lib.sh` prepended. Every line counts: a check passes only if every command
succeeds.

- `! cmd` and `test ... && ...` don't fail a `set -e` script unless they are the last line; lint
  rejects them elsewhere. Write `! cmd || exit 1`, or split the line.
- `producer | grep -q x` is safe in checks (check-lib makes quiet greps drain the pipe), but prefer
  `out="$(producer)"; grep -q x <<<"$out"` when the producer may print a lot.
- A plain YAML scalar must not contain `: `. Use a block scalar (`run: |`).
- Check the **result**, not the method: the effective configuration (`sshd -T`,
  `ansible-config dump --only-changed`, `firewall-cmd --list-all`, `ansible-inventory --list`),
  never the exact text of a file unless the task asks for it.
- Act as the right user: NFS exports squash root (`runuser -u <user> -- cat ...`), RHCE checks use
  `as_student`.
- Expected values that only setup knows (a generated digest, the users of a list) can be stored
  in `/etc/autorelabel/` on the node by the setup script.

Helpers from `check-lib.sh`: `as_student`, `student_sh`, `as_user`, `inventory_hosts <group>`,
`inv_var <host> <var>`, `same_words "a b" "b a"`, `playbook_ok <file>` (exists and passes
`--syntax-check`).

## Self-test

`./autorelabel selftest --exam rhcsa [task ids] [--changed]` runs every task on real VMs:

1. **pre-state**: right after setup, the task must not score full marks;
2. **reference**: `solution*.sh`, reboot, full marks;
3. **alternatives**: each `tests/alt-*` group, reboot, full marks;
4. **mistakes**: each `tests/mistake-*` group, reboot, not full marks.

Compatible tasks share a lab (no common `exclusive` tag, disk budgets fit). Anchors and
`breaks_boot` tasks always run alone, because their tests break what other tasks need. Results
go to `banks/<exam>/selftest.json` with a digest of the task's files; `--changed` re-tests only
tasks whose files changed or that never passed. Console transcripts and every grading round are
kept in the session directory under `.workspace/sessions/`.

## Before you open a pull request

- [ ] The prompt names every value the checks verify, in exam style ("persistently", exact paths
      and names), and nothing else.
- [ ] Every requirement has a check, every check covers a requirement.
- [ ] The task works on RHEL 10 as shipped on the DVD (RHEL 10 differs from 9: yescrypt hashes,
      volatile journal, no `rsync` NEWS file, `atd` enabled by preset, ...).
- [ ] `./autorelabel bank lint <exam>` is clean.
- [ ] RHCE: `scripts/dev/check-rhce-playbooks.py` passes (every playbook your scripts write gets an
      `ansible-playbook --syntax-check` with the lab's ansible-core 2.16; see the script's header).
- [ ] `./autorelabel selftest --exam <exam> <task id>` passes, including at least one mistake test.
- [ ] `solution.md` explains the *why* and the classic mistake, with references to official
      documentation or man pages.
