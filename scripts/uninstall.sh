#!/usr/bin/env bash
# autorelabel uninstaller: removes everything autorelabel created on this host.
#
# Pure bash on purpose: works even if Python or the .venv is broken, and a copy
# of this script (plus the ledger) lives in <lab-storage>/autorelabel/ so you can
# still clean up after deleting the repository folder.
#
#   ./autorelabel uninstall [--dry-run] [--yes] [--keep-box] [--delete-iso]
#
# What it removes (only things autorelabel created, found via the ledger and the
# "autorelabel-" name prefix): libvirt domains/snapshots/volumes/pool/networks,
# VirtualBox VMs and media registrations, the Vagrant box, the lab storage
# subdirectory, .workspace/ and .venv/ in the repo, ~/.config/autorelabel.
# It never removes your ISO (unless --delete-iso), your global Vagrant plugins,
# or anything you installed with sudo; for those it prints the undo commands.
set -uo pipefail

PREFIX="autorelabel"
BOX="autorelabel/rhel10"
SELF_DIR="$(cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")" && pwd -P)"
DRY_RUN=0 ASSUME_YES=0 KEEP_BOX=0 DELETE_ISO=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --keep-box) KEEP_BOX=1 ;;
    --delete-iso) DELETE_ISO=1 ;;
    -h|--help) sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [[ -t 1 ]]; then B=$'\e[1m' R=$'\e[31m' G=$'\e[32m' Y=$'\e[33m' D=$'\e[2m' O=$'\e[0m'; else B='' R='' G='' Y='' D='' O=''; fi

# --- Locate repo and ledgers -------------------------------------------------------
REPO=""
if [[ -f "$SELF_DIR/../autorelabel" && -d "$SELF_DIR/../src/autorelabel" ]]; then
  REPO="$(cd "$SELF_DIR/.." && pwd -P)"
fi
LEDGERS=()
[[ -n "$REPO" && -f "$REPO/.workspace/ledger.tsv" ]] && LEDGERS+=("$REPO/.workspace/ledger.tsv")
[[ -f "$SELF_DIR/ledger.tsv" ]] && LEDGERS+=("$SELF_DIR/ledger.tsv")

STORAGE_DIR=""
ISO_PATH=""
if [[ -n "$REPO" && -f "$REPO/.workspace/config.json" ]]; then
  STORAGE_DIR="$(sed -n 's/.*"storage_dir": *"\([^"]*\)".*/\1/p' "$REPO/.workspace/config.json" | head -1)"
  ISO_PATH="$(sed -n 's/.*"iso_path": *"\([^"]*\)".*/\1/p' "$REPO/.workspace/config.json" | head -1)"
  if [[ -n "$STORAGE_DIR" && -f "$STORAGE_DIR/$PREFIX/ledger.tsv" ]]; then
    LEDGERS+=("$STORAGE_DIR/$PREFIX/ledger.tsv")
  fi
fi
if [[ -z "$REPO" && "$(basename "$SELF_DIR")" == "$PREFIX" ]]; then
  STORAGE_DIR="$(dirname "$SELF_DIR")"   # rescue copy inside <storage>/autorelabel/
fi

ledger_ids() {  # ledger_ids <kind>  -> unique identifiers of that kind
  local f
  for f in "${LEDGERS[@]:-}"; do
    [[ -n "$f" && -f "$f" ]] || continue
    awk -F'\t' -v k="$1" '$2 == k { print $3 }' "$f"
  done | sort -u
}
ledger_details() {  # ledger_details <kind> -> details column
  local f
  for f in "${LEDGERS[@]:-}"; do
    [[ -n "$f" && -f "$f" ]] || continue
    awk -F'\t' -v k="$1" '$2 == k { print $4 }' "$f"
  done | sort -u
}

have() { command -v "$1" >/dev/null 2>&1; }
VIRSH=()
if have virsh && virsh -c qemu:///system uri >/dev/null 2>&1; then VIRSH=(virsh -c qemu:///system); fi
HAVE_VBOX=0; have VBoxManage && HAVE_VBOX=1
HAVE_VAGRANT=0; have vagrant && HAVE_VAGRANT=1
export VAGRANT_CHECKPOINT_DISABLE=1

# --- Discover what exists ------------------------------------------------------------
uniq_lines() { awk 'NF && !seen[$0]++'; }

DOMAINS=() POOLS=() NETWORKS=() VBOX_VMS=() VBOX_MEDIA=() VBOX_HOSTONLY=() UNITS=() DIRS=() BOXES=0

if ((${#VIRSH[@]})); then
  mapfile -t DOMAINS < <({ ledger_ids libvirt-domain; "${VIRSH[@]}" list --all --name 2>/dev/null | grep "^${PREFIX}-"; } \
    | uniq_lines | while read -r d; do "${VIRSH[@]}" dominfo "$d" >/dev/null 2>&1 && echo "$d"; done)
  mapfile -t POOLS < <({ ledger_ids libvirt-pool; "${VIRSH[@]}" pool-list --all --name 2>/dev/null | grep "^${PREFIX}"; } \
    | uniq_lines | while read -r p; do "${VIRSH[@]}" pool-info "$p" >/dev/null 2>&1 && echo "$p"; done)
  mapfile -t NETWORKS < <({ ledger_ids libvirt-network; "${VIRSH[@]}" net-list --all --name 2>/dev/null | grep "^${PREFIX}-"; } \
    | uniq_lines | while read -r n; do "${VIRSH[@]}" net-info "$n" >/dev/null 2>&1 && echo "$n"; done)
fi
if ((HAVE_VBOX)); then
  mapfile -t VBOX_VMS < <({ ledger_ids vbox-vm; VBoxManage list vms 2>/dev/null | sed -n "s/^\"\(${PREFIX}-[^\"]*\)\".*/\1/p"; } \
    | uniq_lines | while read -r v; do VBoxManage showvminfo "$v" >/dev/null 2>&1 && echo "$v"; done)
  mapfile -t VBOX_MEDIA < <(ledger_ids vbox-medium | uniq_lines)
  mapfile -t VBOX_HOSTONLY < <(ledger_ids vbox-hostonly | uniq_lines)
fi
if have systemctl; then
  mapfile -t UNITS < <(systemctl --user list-units "${PREFIX}-*" --all --plain --no-legend 2>/dev/null | awk '{print $1}' | uniq_lines)
fi
if ((HAVE_VAGRANT)) && ((KEEP_BOX == 0)); then
  if vagrant box list 2>/dev/null | grep -q "^${BOX} "; then BOXES=1; fi
fi

safe_dir() {  # only ever delete our own directories
  local d="$1"
  [[ -n "$d" && "$d" != "/" && "$d" != "$HOME" && "$d" != "$HOME/" ]] || return 1
  case "$d" in
    */"$PREFIX"|*/"$PREFIX"/*|*/.workspace|*/.workspace/*|*/.venv|/tmp/"$PREFIX"-*) return 0 ;;
  esac
  return 1
}
mapfile -t DIRS < <({
  ledger_ids dir
  [[ -n "$STORAGE_DIR" ]] && echo "$STORAGE_DIR/$PREFIX"
  [[ -d "$HOME/.config/$PREFIX" ]] && echo "$HOME/.config/$PREFIX"
  # SSH connection-sharing sockets (tmpfs; would vanish at logout anyway)
  [[ -n "${XDG_RUNTIME_DIR:-}" ]] && echo "$XDG_RUNTIME_DIR/$PREFIX"
  echo "/tmp/$PREFIX-$(id -u)"
} | uniq_lines | while read -r d; do [[ -e "$d" ]] && safe_dir "$d" && echo "$d"; done)

# --- Show the plan --------------------------------------------------------------------
echo "${B}autorelabel uninstall${O}"
[[ -n "$REPO" ]] && echo "${D}repository: $REPO${O}"
((${#LEDGERS[@]})) && echo "${D}ledger(s): ${LEDGERS[*]}${O}"
echo
nothing=1
section() { local title="$1"; shift; (($#)) || return 0; nothing=0; echo "${B}$title${O}"; printf '  - %s\n' "$@"; }
section "libvirt domains (with snapshots and disks)" "${DOMAINS[@]}"
section "libvirt storage pools (all volumes inside)" "${POOLS[@]}"
section "libvirt networks" "${NETWORKS[@]}"
section "VirtualBox VMs" "${VBOX_VMS[@]}"
section "VirtualBox media registrations (files are kept)" "${VBOX_MEDIA[@]}"
section "VirtualBox host-only interfaces" "${VBOX_HOSTONLY[@]}"
section "systemd user units" "${UNITS[@]}"
((BOXES)) && section "Vagrant box" "$BOX (all providers and versions)"
section "directories" "${DIRS[@]}"
REPO_ITEMS=()
if [[ -n "$REPO" ]]; then
  for d in "$REPO/.workspace" "$REPO/.venv"; do [[ -e "$d" ]] && REPO_ITEMS+=("$d"); done
  while IFS= read -r d; do REPO_ITEMS+=("$d"); done < <(find "$REPO/src" "$REPO/tests" -type d -name __pycache__ 2>/dev/null)
fi
section "repository runtime files" "${REPO_ITEMS[@]}"
if ((DELETE_ISO)) && [[ -n "$ISO_PATH" && -f "$ISO_PATH" ]]; then section "ISO (--delete-iso)" "$ISO_PATH"; fi

mapfile -t USER_UNDO < <(ledger_details user-action | uniq_lines)

if ((nothing)); then
  echo "${G}Nothing to remove. This host has no autorelabel artifacts.${O}"
else
  echo
  if ((DRY_RUN)); then echo "${Y}Dry run: nothing was changed.${O}"; fi
fi
if ((DRY_RUN)) || ((nothing)); then
  if ((${#USER_UNDO[@]})); then
    echo; echo "${B}Steps you ran yourself during setup (undo them only if you want to):${O}"
    printf '  %s\n' "${USER_UNDO[@]}"
  fi
  exit 0
fi

if ((ASSUME_YES == 0)); then
  if [[ ! -t 0 ]]; then echo "${R}Refusing to proceed without a terminal; use --yes.${O}" >&2; exit 1; fi
  read -r -p "Remove all of the above? [y/N] " answer
  [[ "$answer" =~ ^[Yy]([Ee][Ss])?$ ]] || { echo "Cancelled."; exit 1; }
fi

# --- Execute (tolerant: keep going, collect failures) -----------------------------------
FAILED=()
step() {  # step "<description>" cmd...
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "  ${G}✔${O} $desc"; else echo "  ${R}✘${O} $desc"; FAILED+=("$desc"); fi
}
quiet() { "$@" >/dev/null 2>&1 || true; }

for u in "${UNITS[@]}"; do step "stop $u" systemctl --user stop "$u"; done

for d in "${DOMAINS[@]}"; do
  quiet "${VIRSH[@]}" destroy "$d"
  while read -r s; do [[ -n "$s" ]] && quiet "${VIRSH[@]}" snapshot-delete "$d" "$s"; done \
    < <("${VIRSH[@]}" snapshot-list "$d" --name 2>/dev/null)
  step "remove domain $d" "${VIRSH[@]}" undefine "$d" --remove-all-storage --snapshots-metadata --managed-save
done
for p in "${POOLS[@]}"; do
  quiet "${VIRSH[@]}" pool-start "$p"
  while read -r v; do [[ -n "$v" ]] && quiet "${VIRSH[@]}" vol-delete --pool "$p" "$v"; done \
    < <("${VIRSH[@]}" vol-list --pool "$p" --name 2>/dev/null)
  quiet "${VIRSH[@]}" pool-destroy "$p"
  quiet "${VIRSH[@]}" pool-delete "$p"
  step "remove storage pool $p" "${VIRSH[@]}" pool-undefine "$p"
done
for n in "${NETWORKS[@]}"; do
  quiet "${VIRSH[@]}" net-destroy "$n"
  step "remove network $n" "${VIRSH[@]}" net-undefine "$n"
done
for v in "${VBOX_VMS[@]}"; do
  quiet VBoxManage controlvm "$v" poweroff
  sleep 1
  step "remove VirtualBox VM $v" VBoxManage unregistervm "$v" --delete
done
for m in "${VBOX_MEDIA[@]}"; do quiet VBoxManage closemedium dvd "$m"; echo "  ${G}✔${O} unregister medium $m"; done
for h in "${VBOX_HOSTONLY[@]}"; do
  if VBoxManage hostonlyif remove "$h" >/dev/null 2>&1 || VBoxManage hostonlynet remove --name="$h" >/dev/null 2>&1; then
    echo "  ${G}✔${O} remove host-only network $h"
  else
    echo "  ${R}✘${O} remove host-only network $h"; FAILED+=("host-only network $h")
  fi
done
if ((BOXES)); then
  step "remove Vagrant box $BOX" vagrant box remove --force --all "$BOX"
fi
((HAVE_VAGRANT)) && quiet vagrant global-status --prune

for d in "${DIRS[@]}"; do step "delete $d" rm -rf -- "$d"; done
for d in "${REPO_ITEMS[@]}"; do step "delete $d" rm -rf -- "$d"; done
if ((DELETE_ISO)) && [[ -n "$ISO_PATH" && -f "$ISO_PATH" ]]; then step "delete $ISO_PATH" rm -f -- "$ISO_PATH"; fi

# --- Verify -----------------------------------------------------------------------------------
echo
LEFT=()
if ((${#VIRSH[@]})); then
  while read -r x; do [[ -n "$x" ]] && LEFT+=("libvirt domain $x"); done < <("${VIRSH[@]}" list --all --name 2>/dev/null | grep "^${PREFIX}-")
  while read -r x; do [[ -n "$x" ]] && LEFT+=("libvirt pool $x"); done < <("${VIRSH[@]}" pool-list --all --name 2>/dev/null | grep "^${PREFIX}")
  while read -r x; do [[ -n "$x" ]] && LEFT+=("libvirt network $x"); done < <("${VIRSH[@]}" net-list --all --name 2>/dev/null | grep "^${PREFIX}-")
fi
if ((HAVE_VBOX)); then
  while read -r x; do [[ -n "$x" ]] && LEFT+=("VirtualBox VM $x"); done < <(VBoxManage list vms 2>/dev/null | sed -n "s/^\"\(${PREFIX}-[^\"]*\)\".*/\1/p")
fi
if ((HAVE_VAGRANT)) && ((KEEP_BOX == 0)) && vagrant box list 2>/dev/null | grep -q "^${BOX} "; then LEFT+=("Vagrant box $BOX"); fi
for d in "${DIRS[@]}" "${REPO_ITEMS[@]}"; do [[ -e "$d" ]] && LEFT+=("$d"); done

if ((${#LEFT[@]})); then
  echo "${R}${B}Some items could not be removed:${O}"
  printf '  - %s\n' "${LEFT[@]}"
  echo "Re-run ./autorelabel uninstall, or remove them manually (libvirt objects with virsh)."
  STATUS=1
else
  echo "${G}${B}Host is clean ✓${O}  Everything autorelabel created has been removed."
  [[ -n "$REPO" ]] && echo "${D}You can now delete the repository folder: rm -rf '$REPO'${O}"
  STATUS=0
fi
if ((KEEP_BOX)); then echo "${D}Kept the Vagrant box ($BOX) as requested.${O}"; fi
if [[ -n "$ISO_PATH" && -f "$ISO_PATH" ]]; then echo "${D}Your ISO was kept: $ISO_PATH${O}"; fi
if ((${#USER_UNDO[@]})); then
  echo; echo "${B}Steps you ran yourself during setup (undo them only if you want to):${O}"
  printf '  %s\n' "${USER_UNDO[@]}"
fi
exit "$STATUS"
