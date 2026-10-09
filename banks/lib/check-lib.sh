# shellcheck shell=bash
# Read-only helpers available to every check. Defines functions only.

# Checks run with pipefail, so `producer | grep -q x` could fail at random: grep exits at the
# first match and a producer still writing gets SIGPIPE. Quiet greps on a pipe drain it.
grep() {
  local a quiet=0
  for a in "$@"; do
    case "$a" in --) break ;; --quiet|--silent) quiet=1 ;; --*) ;; -*q*) quiet=1 ;; esac
  done
  # AR_STDIN_ISOLATED: the runner gave the script /dev/null as stdin, so a pipe here is a pipeline
  if ((quiet)) && [[ -n "${AR_STDIN_ISOLATED:-}" && -p /dev/stdin ]]; then
    local rc=0
    command grep "$@" || rc=$?
    cat >/dev/null 2>&1 || true
    return "$rc"
  fi
  command grep "$@"
}

# as_student <command> [args...]: run a command as the RHCE candidate, in the project
# directory, with a login-like environment (so ansible.cfg in that directory applies).
as_student() {
  local uid; uid="$(id -u student)"
  (cd /home/student/ansible 2>/dev/null || cd /home/student || exit 1
   runuser -u student -- env -i HOME=/home/student USER=student LOGNAME=student LANG=C.UTF-8 \
     PATH=/usr/local/bin:/usr/bin:/usr/sbin:/bin:/sbin XDG_RUNTIME_DIR="/run/user/$uid" \
     ANSIBLE_NOCOLOR=1 ANSIBLE_DEPRECATION_WARNINGS=0 "$@")
}

# student_sh '<shell code>': like as_student, for pipelines and redirections.
student_sh() { as_student bash -c "$1"; }

# inventory_hosts <group>: hosts of a group per the candidate's inventory (short names, sorted).
inventory_hosts() {
  as_student ansible-inventory --list 2>/dev/null | python3 -c '
import json, sys
inv = json.load(sys.stdin); seen = set()
def walk(g):
    d = inv.get(g, {})
    for h in d.get("hosts", []): seen.add(h.split(".")[0])
    for c in d.get("children", []): walk(c)
walk(sys.argv[1]); print(" ".join(sorted(seen)))' "$1"
}

# same_words "<a b c>" "<c b a>": true if both lists contain the same words.
same_words() { test "$(tr ' ' '\n' <<<"$1" | sed '/^$/d' | sort -u)" = "$(tr ' ' '\n' <<<"$2" | sed '/^$/d' | sort -u)"; }

# inv_var <short-host> <variable>: a host variable as the candidate's inventory resolves it
# (group_vars / host_vars next to the inventory included). Prints nothing if undefined.
inv_var() {
  as_student ansible-inventory --list 2>/dev/null | python3 -c '
import json, sys
meta = json.load(sys.stdin).get("_meta", {}).get("hostvars", {})
for name, hv in meta.items():
    if name.split(".")[0] == sys.argv[1] and sys.argv[2] in hv:
        v = hv[sys.argv[2]]
        print(v if isinstance(v, str) else json.dumps(v))
        break' "$1" "$2"
}

# playbook_ok <file>: the playbook exists in the project directory and passes a syntax check.
playbook_ok() {
  test -s "/home/student/ansible/$1"
  as_student ansible-playbook --syntax-check "$1" >/dev/null
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
