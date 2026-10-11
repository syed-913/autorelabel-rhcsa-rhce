#!/usr/bin/env bash
# Prepended to every task setup/solution/test script by the engine.
# Parameters arrive as P_<NAME>, lab facts as LAB_<PATH> (e.g. LAB_NODE1_IP).
set -Eeuo pipefail
trap 'echo "ERROR: line $LINENO: $BASH_COMMAND" >&2' ERR
export LC_ALL=C

# Install packages during setup. The engine provides a temporary repository
# (removed again before the exam starts), so this never leaks into the exam.
ar_install() { dnf -y -q install "$@" >/dev/null; }

# Lab interface of this node (discovered at provisioning time).
ar_lab_nic() { sed -n 's/^lab_nic=//p' /etc/autorelabel/facts; }

# Write a file only if its content differs (keeps setups idempotent).
ar_write() {  # ar_write <path> <mode>   (content on stdin)
  local path="$1" mode="${2:-0644}" tmp
  tmp="$(mktemp)"
  cat > "$tmp"
  install -D -m "$mode" "$tmp" "$path"
  rm -f "$tmp"
}

# Create a local user with a password (idempotent).
ar_user() {  # ar_user <name> <password> [extra useradd args...]
  local name="$1" pw="$2"; shift 2
  id "$name" >/dev/null 2>&1 || useradd "$@" "$name"
  echo "$name:$pw" | chpasswd
}

# Copy an SSH public key to another host the way a candidate would with ssh-copy-id,
# answering the password prompt (used by reference solutions in self-tests).
ar_ssh_copy_id() {  # ar_ssh_copy_id <local-user> <remote-user@host> <password>
  local user="$1" target="$2" pw="$3"
  sudo -H -u "$user" python3 - "$target" "$pw" <<'PY'
import os, pty, sys, time
target, pw = sys.argv[1], sys.argv[2]
pid, fd = pty.fork()
if pid == 0:
    os.execvp("ssh-copy-id", ["ssh-copy-id", "-o", "StrictHostKeyChecking=accept-new", target])
buf = b""
deadline = time.time() + 60
while time.time() < deadline:
    try:
        data = os.read(fd, 1024)
    except OSError:
        break
    if not data:
        break
    buf += data
    if b"password:" in buf.lower():
        os.write(fd, pw.encode() + b"\n")
        buf = b""
_, status = os.waitpid(pid, 0)
sys.exit(os.waitstatus_to_exitcode(status))
PY
}

# Deterministic test data (identical bytes on every node for the same word), so a
# check on one node can verify content created on another without network access.
ar_gen_tree() {  # ar_gen_tree <dir> <word>
  local dir="$1" word="$2" f i
  mkdir -p "$dir/sub"
  for f in index.txt notes.md sub/a.txt sub/b.txt; do
    for i in $(seq 1 40); do echo "$word $f line $i"; done > "$dir/$f"
  done
  chmod 0644 "$dir/index.txt" "$dir/sub/a.txt"; chmod 0600 "$dir/notes.md"; chmod 0640 "$dir/sub/b.txt"
  touch -d '2025-01-15 10:00:00 UTC' "$dir/index.txt" "$dir/notes.md"
  touch -d '2024-06-01 08:30:00 UTC' "$dir/sub/a.txt" "$dir/sub/b.txt"
}
ar_tree_digest() {  # content + modes + mtimes of all files under <dir>
  (cd "$1" && find . -type f -printf '%P %m %T@\n' | sort && find . -type f -exec sha256sum {} + | sort) \
    | sha256sum | cut -d' ' -f1
}
ar_gen_tar() {  # ar_gen_tar <file.tar> <word>
  local out="$1" word="$2" tmp
  tmp="$(mktemp -d)"
  ar_gen_tree "$tmp/cfg" "$word"
  tar --format=gnu --sort=name --owner=0 --group=0 --numeric-owner --mtime='2025-01-01 00:00:00 UTC' \
      -C "$tmp" -cf "$out" cfg
  rm -rf "$tmp"
}

# Append a GPT partition of <size> MiB to <disk> and print its device path. Several tasks
# can share one disk: each appends after the existing partitions.
ar_new_partition() {  # ar_new_partition <disk> <size-MiB> [type: linux|lvm|swap]
  local disk="$1" size="$2" type="${3:-linux}" code before after
  case "$type" in lvm) code=E6D6D379-F507-44C2-A23C-238F2A3DF928 ;;
                  swap) code=0657FD6D-A4AB-43C4-84E5-0933C84B4F4F ;;
                  *) code=0FC63DAF-8483-4772-8E79-3D69D8477DE4 ;; esac
  if ! sfdisk -d "$disk" >/dev/null 2>&1; then echo 'label: gpt' | sfdisk -q "$disk" >/dev/null; fi
  before="$(lsblk -nrpo NAME "$disk" | tail -n +2 | sort)"
  echo ",${size}M,${code}" | sfdisk -q --append --no-reread "$disk" >/dev/null 2>&1 || true
  partprobe "$disk" 2>/dev/null || partx -u "$disk" 2>/dev/null || true
  udevadm settle
  after="$(lsblk -nrpo NAME "$disk" | tail -n +2 | sort)"
  comm -13 <(echo "$before") <(echo "$after") | sed -n 1p
}

# Deterministic content for "data must survive" checks.
ar_fill() {  # ar_fill <dir> <word>  -> writes files and records their digest in <dir>/.ar-digest
  local dir="$1" word="$2" i
  mkdir -p "$dir" /etc/autorelabel
  for i in 1 2 3 4 5; do for _ in $(seq 1 200); do echo "$word record $i"; done > "$dir/data-$i.txt"; done
  (cd "$dir" && sha256sum data-*.txt) > /etc/autorelabel/"$word"-data.sha256
}

# --- RHCE helpers --------------------------------------------------------------------------------
as_student() {  # as_student <command> [args...]: run as the candidate in ~/ansible
  local uid; uid="$(id -u student)"
  (cd /home/student/ansible 2>/dev/null || cd /home/student || exit 1
   runuser -u student -- env -i HOME=/home/student USER=student LOGNAME=student LANG=C.UTF-8 \
     PATH=/usr/local/bin:/usr/bin:/usr/sbin:/bin:/sbin XDG_RUNTIME_DIR="/run/user/$uid" \
     ANSIBLE_NOCOLOR=1 ANSIBLE_DEPRECATION_WARNINGS=0 "$@")
}
student_sh() { as_student bash -c "$1"; }
student_write() {  # student_write <path relative to ~/ansible> [mode]  (content on stdin)
  local p="/home/student/ansible/$1"
  runuser -u student -- mkdir -p "$(dirname "$p")"
  cat > "$p"; chown student:student "$p"; chmod "${2:-0644}" "$p"
}

# as_user <user> <command> [args...]: run as a user with a clean, login-like environment.
# (Not sudo: tools like `flatpak --user` refuse to run when SUDO_USER is set.)
as_user() {
  local u="$1"; shift
  local home; home="$(getent passwd "$u" | cut -d: -f6)"
  (cd "$home" 2>/dev/null || cd / || exit 1
   runuser -u "$u" -- env -i HOME="$home" USER="$u" LOGNAME="$u" LANG=C.UTF-8 \
     PATH=/usr/local/bin:/usr/bin:/usr/sbin:/bin:/sbin XDG_RUNTIME_DIR="/run/user/$(id -u "$u")" "$@")
}
