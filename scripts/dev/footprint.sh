#!/usr/bin/env bash
# Snapshot everything on this host that autorelabel, or the tools it drives (Vagrant, Packer,
# VirtualBox, libvirt, ssh, pip), could create or change. Used for the install → uninstall audit:
# take a snapshot on a clean host, install and use autorelabel, run ./autorelabel uninstall,
# take another snapshot, and diff the two. They must be identical.
#
#   scripts/dev/footprint.sh <out-file> [<lab storage directory>]
#   diff -u clean.txt after-uninstall.txt
#
# Read-only and needs no root (root-only places such as the firewall are not covered).
set -uo pipefail

out="${1:?usage: footprint.sh <out-file> [<lab storage directory>]}"
storage="${2:-}"
ROOT="$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")/../.." && pwd -P)"
export LC_ALL=C VAGRANT_CHECKPOINT_DISABLE=1
TOOLS='autorelabel|vagrant|packer|vbox|virtualbox|libvirt|qemu|ansible|dnsmasq'

section() { printf '\n## %s\n' "$1"; }
tree() {  # every entry below a directory: type, size of files, relative path
  local d
  for d in "$@"; do
    printf -- '-- %s\n' "${d/#$HOME/~}"
    [[ -e "$d" ]] || { echo "(absent)"; continue; }
    find "$d" -xdev -mindepth 1 \( -type f -printf 'f %s %P\n' \) -o \( -type d -printf 'd - %P\n' \) \
      -o \( -type l -printf 'l - %P -> %l\n' \) 2>/dev/null | sort
  done
}
names() {  # the entries directly inside a directory
  local d
  for d in "$@"; do
    printf -- '-- %s\n' "${d/#$HOME/~}"
    if [[ -d "$d" ]]; then find "$d" -mindepth 1 -maxdepth 1 -printf '%f\n' 2>/dev/null | sort; else echo "(absent)"; fi
  done
}
digest() {  # content hashes of individual files
  local f
  for f in "$@"; do
    if [[ -f "$f" ]]; then printf '%s  %s\n' "$(sha256sum < "$f" | cut -c1-16)" "${f/#$HOME/~}"
    else printf '(absent)  %s\n' "${f/#$HOME/~}"; fi
  done
}
have() { command -v "$1" >/dev/null 2>&1; }

{
  section "home directory"
  names "$HOME" "$HOME/.config" "$HOME/.local/share" "$HOME/.local/state" "$HOME/.cache"
  tree "$HOME/.local/bin"

  section "Vagrant"
  tree "$HOME/.vagrant.d"
  digest "$HOME/.vagrant.d/data/machine-index/index"
  if have vagrant; then
    vagrant box list 2>&1
    vagrant plugin list 2>&1
    vagrant global-status 2>&1 | sed -n '/^id /,/^ *$/p'
  fi

  section "Packer, Ansible, pip"
  tree "$HOME/.packer.d" "$HOME/.config/packer" "$HOME/.cache/packer" "$HOME/.local/share/packer" \
       "$HOME/.ansible" "$HOME/.cache/pip"
  names "$HOME/.local/lib"

  section "VirtualBox (default profile)"
  # VBoxSVC.log* rotate whenever a VBoxSVC starts (this script's own queries start one).
  tree "$HOME/.config/VirtualBox" "$HOME/VirtualBox VMs" | grep -vE ' VBoxSVC\.log(\.[0-9]+)?$'
  digest "$HOME/.config/VirtualBox/VirtualBox.xml"
  if have VBoxManage; then
    # One VBoxSVC per user: let a service for another profile exit first.
    for _ in $(seq 1 60); do pgrep -u "$(id -u)" -x VBoxSVC >/dev/null || break; sleep 1; done
    for what in vms hdds dvds floppies hostonlyifs hostonlynets natnets dhcpservers extpacks; do
      printf -- '-- list %s\n' "$what"
      env -u VBOX_USER_HOME VBoxManage list "$what" 2>&1 \
        | grep -E '^("|Name:|Location:|NetworkName:|Pack no|Extension Packs:)' || true
    done
    env -u VBOX_USER_HOME VBoxManage list systemproperties 2>&1 | grep -E '^Default (machine folder|Hard Disk format)'
  fi

  section "libvirt"
  if have virsh; then
    for uri in qemu:///system qemu:///session; do
      printf -- '-- %s\n' "$uri"
      virsh -c "$uri" list --all --name 2>&1 | sed 's/ *$//' | sed '/^$/d'
      virsh -c "$uri" net-list --all --name 2>&1 | sed 's/ *$//' | sed '/^$/d' | sed 's/^/net /'
      while read -r pool; do
        [[ -n "$pool" ]] || continue
        echo "pool $pool"
        virsh -c "$uri" vol-list --pool "$pool" 2>/dev/null | awk 'NR > 2 && NF { print "  vol " $1 }'
      done < <(virsh -c "$uri" pool-list --all --name 2>/dev/null | sed 's/ *$//')
      virsh -c "$uri" nwfilter-list 2>/dev/null | awk 'NR > 2 && NF { print "nwfilter " $2 }'
      virsh -c "$uri" secret-list 2>/dev/null | awk 'NR > 2 && NF { print "secret " $1 }'
    done
  fi
  names /etc/libvirt/qemu /etc/libvirt/qemu/networks /etc/libvirt/storage /var/lib/libvirt/dnsmasq \
        /var/lib/libvirt/images /var/log/libvirt/qemu 2>/dev/null
  tree "$HOME/.config/libvirt" "$HOME/.local/share/libvirt" "$HOME/.cache/libvirt"

  section "network interfaces and routes"
  ip -br link 2>/dev/null | awk '{ print $1 }' | sort
  ip -4 -br addr 2>/dev/null | awk '{ $2 = ""; print }' | sort
  ip -4 route 2>/dev/null | sort

  section "SSH"
  names "$HOME/.ssh"
  digest "$HOME/.ssh/known_hosts" "$HOME/.ssh/config"

  section "systemd user units, cron, processes"
  systemctl --user list-unit-files --no-legend 2>/dev/null | awk '{ print $1, $2 }' | sort
  systemctl --user list-units --all --plain --no-legend 2>/dev/null | awk '{ print $1 }' \
    | grep -iE "$TOOLS" || echo "(no matching units)"
  crontab -l 2>&1 | sed 's/^/cron: /'
  # shellcheck disable=SC2009  # full command lines are what we compare
  ps -u "$(id -u)" -o args= 2>/dev/null | grep -iE "$TOOLS" | grep -vE 'footprint\.sh|grep ' \
    | sed 's/ \{2,\}/ /g' | sort || echo "(no matching processes)"

  section "temporary and runtime directories"
  find /tmp /var/tmp -maxdepth 1 -mindepth 1 -user "$(id -u)" -printf '%p\n' 2>/dev/null \
    | grep -iE "$TOOLS" | sort || echo "(nothing matching in /tmp, /var/tmp)"
  names "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" | grep -iE "^--|$TOOLS" || true

  section "kernel modules"
  lsmod 2>/dev/null | awk 'NR > 1 { print $1 }' | sort

  section "lab storage directory"
  if [[ -n "$storage" ]]; then names "$storage"; else echo "(not given)"; fi

  section "repository: ignored and untracked files"
  git -C "$ROOT" status --porcelain --ignored 2>&1 | sort
} > "$out" 2>&1

echo "footprint snapshot: $out ($(wc -l < "$out") lines)"
