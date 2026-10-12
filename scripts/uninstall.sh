#!/usr/bin/env bash
# autorelabel uninstaller: removes everything autorelabel created on this host.
#
# Pure bash on purpose: works even if the .venv is broken (the system python3 is
# only used, when present, to edit Vagrant's machine index), and a copy of this
# script (plus the ledger) lives in <lab-storage>/autorelabel/ so you can still
# clean up after deleting the repository folder.
#
#   ./autorelabel uninstall [--dry-run] [--yes] [--keep-box] [--delete-iso]
#
# What it removes (only things autorelabel created, found via the ledger and the
# "autorelabel-" name prefix): libvirt domains/snapshots/volumes/pool/networks,
# VirtualBox VMs and media registrations, the Vagrant box and autorelabel's
# entries in Vagrant's machine index, the lab storage subdirectory, .workspace/
# and .venv/ in the repo, ~/.config/autorelabel. It never removes your ISO
# (unless --delete-iso), your Vagrant plugins, other Vagrant projects' entries,
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
    -h|--help) awk 'NR > 1 && !/^#/ { exit } NR > 1 { sub(/^# ?/, ""); print }' "${BASH_SOURCE[0]}"; exit 0 ;;
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
# autorelabel keeps its VMs in a private VirtualBox profile inside the lab storage; older
# versions (and interrupted runs) may have left VMs in your default profile, so both are cleaned.
VBOX_PRIVATE=""
[[ -n "$STORAGE_DIR" && -d "$STORAGE_DIR/$PREFIX/virtualbox/profile" ]] && VBOX_PRIVATE="$(readlink -m -- "$STORAGE_DIR/$PREFIX/virtualbox/profile")"
# VirtualBox runs one VBoxSVC per user, bound to the profile it started with: a VBoxManage
# command for another profile silently acts on the running one. So before using a profile, wait
# for a VBoxSVC serving another one to exit (an idle one does within about 5 s).
vbox_svc_homes() {  # the profile each of our running VBoxSVCs serves (empty line: default)
  local pid home
  for pid in $(pgrep -u "$(id -u)" -x VBoxSVC 2>/dev/null); do
    home="$(tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | sed -n 's/^VBOX_USER_HOME=//p')"
    if [[ -n "$home" ]]; then readlink -m -- "$home"; else echo; fi
  done
}
vbox_wait() {  # vbox_wait <only|none> <private|default>: VBoxSVC serves only that profile / not it
  local mode="$1" want="" h i busy
  [[ "$2" == private ]] && want="$VBOX_PRIVATE"
  for ((i = 0; i < 60; i++)); do
    busy=0
    while IFS= read -r h; do
      if [[ "$mode" == only && "$h" != "$want" ]] || [[ "$mode" == none && "$h" == "$want" ]]; then busy=1; fi
    done < <(vbox_svc_homes)
    ((busy)) || return 0
    sleep 1
  done
  return 1
}
vbm() {  # vbm <private|default> <VBoxManage args...>
  local prof="$1"; shift
  vbox_wait only "$prof" || return 1
  if [[ "$prof" == private ]]; then VBOX_USER_HOME="$VBOX_PRIVATE" VBoxManage "$@"
  else env -u VBOX_USER_HOME VBoxManage "$@"; fi
}
VBOX_SKIPPED=()   # profiles VirtualBox could not switch to (VirtualBox Manager or VMs kept it busy)
vbox_profiles() {
  local p
  for p in ${VBOX_PRIVATE:+private} default; do
    [[ " ${VBOX_SKIPPED[*]} " == *" $p "* ]] || echo "$p"
  done
}
vbox_label() { [[ "$1" == private ]] && echo "autorelabel's VirtualBox profile" || echo "your default VirtualBox profile"; }
HAVE_VAGRANT=0; have vagrant && HAVE_VAGRANT=1
export VAGRANT_CHECKPOINT_DISABLE=1
# Vagrant's global machine index (vagrant global-status) lists the machines of every Vagrant
# project on this host. Only autorelabel's entries (its Vagrantfile) are removed: `vagrant
# global-status --prune` would also drop the stale entries of your other projects.
VAGRANT_INDEX="${VAGRANT_HOME:-$HOME/.vagrant.d}/data/machine-index/index"
vagrant_index() {  # vagrant_index <count|remove>: autorelabel's machine-index entries
  [[ -n "$REPO" && -f "$VAGRANT_INDEX" ]] && have python3 && have flock || return 1
  flock "$VAGRANT_INDEX.lock" python3 -I - "$1" "$VAGRANT_INDEX" "$REPO/vagrant" <<'PY'
import json, os, sys, tempfile
action, path, ours = sys.argv[1:]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
machines = data.get("machines", {})
keep = {k: m for k, m in machines.items() if m.get("vagrantfile_path") != ours}
if action == "count":
    print(len(machines) - len(keep))
elif len(keep) != len(machines):
    data["machines"] = keep
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, separators=(",", ":"), ensure_ascii=False)   # as Vagrant writes it
    os.chmod(tmp, os.stat(path).st_mode & 0o7777)
    os.replace(tmp, path)
PY
}

# --- Discover what exists ------------------------------------------------------------
uniq_lines() { awk '{ sub(/[ \t]+$/, "") } NF && !seen[$0]++'; }   # virsh pads --name output

DOMAINS=() POOLS=() NETWORKS=() VBOX_VMS=() VBOX_MEDIA=() VBOX_HOSTONLY=() UNITS=() DIRS=() BOXES=0

if ((${#VIRSH[@]})); then
  mapfile -t DOMAINS < <({ ledger_ids libvirt-domain; "${VIRSH[@]}" list --all --name 2>/dev/null | grep "^${PREFIX}-"; } \
    | uniq_lines | while read -r d; do "${VIRSH[@]}" dominfo "$d" >/dev/null 2>&1 && echo "$d"; done)
  mapfile -t POOLS < <({ ledger_ids libvirt-pool; "${VIRSH[@]}" pool-list --all --name 2>/dev/null | grep "^${PREFIX}"; } \
    | uniq_lines | while read -r p; do "${VIRSH[@]}" pool-info "$p" >/dev/null 2>&1 && echo "$p"; done)
  mapfile -t NETWORKS < <({ ledger_ids libvirt-network; "${VIRSH[@]}" net-list --all --name 2>/dev/null | grep "^${PREFIX}-"; } \
    | uniq_lines | while read -r n; do "${VIRSH[@]}" net-info "$n" >/dev/null 2>&1 && echo "$n"; done)
fi
VBOX_SHOW=()
if ((HAVE_VBOX)); then
  while read -r prof; do
    if ! vbox_wait only "$prof"; then VBOX_SKIPPED+=("$prof"); continue; fi
    while read -r v; do
      [[ -n "$v" ]] || continue
      VBOX_VMS+=("$prof:$v"); VBOX_SHOW+=("$v ($(vbox_label "$prof"))")
    done < <({ ledger_ids vbox-vm; vbm "$prof" list vms 2>/dev/null | sed -n "s/^\"\(${PREFIX}-[^\"]*\)\".*/\1/p"; } \
      | uniq_lines | while read -r v; do vbm "$prof" showvminfo "$v" >/dev/null 2>&1 && echo "$v"; done)
  done < <(vbox_profiles)
  mapfile -t VBOX_MEDIA < <(ledger_ids vbox-medium | uniq_lines)
  mapfile -t VBOX_HOSTONLY < <(ledger_ids vbox-hostonly | uniq_lines)
fi
if have systemctl; then
  mapfile -t UNITS < <(systemctl --user list-units "${PREFIX}-*" --all --plain --no-legend 2>/dev/null | awk '{print $1}' | uniq_lines)
fi
if ((HAVE_VAGRANT)) && ((KEEP_BOX == 0)); then
  if vagrant box list 2>/dev/null | grep -q "^${BOX} "; then BOXES=1; fi
fi
INDEX_ENTRIES="$(vagrant_index count 2>/dev/null || echo 0)"

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
section "VirtualBox VMs" "${VBOX_SHOW[@]}"
section "VirtualBox media registrations (files are kept)" "${VBOX_MEDIA[@]}"
section "VirtualBox host-only interfaces" "${VBOX_HOSTONLY[@]}"
section "systemd user units" "${UNITS[@]}"
((BOXES)) && section "Vagrant box" "$BOX (all providers and versions)"
((INDEX_ENTRIES > 0)) && section "Vagrant machine index (vagrant global-status)" "$INDEX_ENTRIES autorelabel entries"
section "directories" "${DIRS[@]}"
REPO_ITEMS=()
if [[ -n "$REPO" ]]; then
  for d in "$REPO/.workspace" "$REPO/.venv"; do [[ -e "$d" ]] && REPO_ITEMS+=("$d"); done
  while IFS= read -r d; do REPO_ITEMS+=("$d"); done < <(find "$REPO/src" "$REPO/tests" -type d -name __pycache__ 2>/dev/null)
fi
section "repository runtime files" "${REPO_ITEMS[@]}"
for p in "${VBOX_SKIPPED[@]}"; do
  if [[ "$p" == private ]]; then
    echo "${Y}VirtualBox Manager or your own VMs kept VirtualBox busy, so autorelabel's VirtualBox profile${O}"
    echo "${Y}was not opened. Its VMs are deleted together with the lab storage folder.${O}"
  else
    echo "${Y}VirtualBox stayed busy with autorelabel's profile, so your default VirtualBox profile was not${O}"
    echo "${Y}checked for VMs left by older versions. Run the uninstaller again afterwards to check it.${O}"
  fi
done
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
for pv in "${VBOX_VMS[@]}"; do
  prof="${pv%%:*}" v="${pv#*:}"
  quiet vbm "$prof" controlvm "$v" poweroff
  sleep 1
  step "remove VirtualBox VM $v" vbm "$prof" unregistervm "$v" --delete
done
for prof in $( ((${#VBOX_MEDIA[@]})) && vbox_profiles); do
  for m in "${VBOX_MEDIA[@]}"; do quiet vbm "$prof" closemedium dvd "$m"; done
done
for m in "${VBOX_MEDIA[@]}"; do echo "  ${G}✔${O} unregister medium $m"; done
for h in "${VBOX_HOSTONLY[@]}"; do
  removed=0
  for prof in $(vbox_profiles); do   # host-only interfaces are system-wide: any profile can remove them
    if vbm "$prof" hostonlyif remove "$h" >/dev/null 2>&1 || vbm "$prof" hostonlynet remove --name="$h" >/dev/null 2>&1; then
      removed=1; break
    fi
  done
  if ((removed)); then
    echo "  ${G}✔${O} remove host-only network $h"
  else
    echo "  ${R}✘${O} remove host-only network $h"; FAILED+=("host-only network $h")
  fi
done
if ((BOXES)); then
  step "remove Vagrant box $BOX" vagrant box remove --force --all "$BOX"
fi
if ((INDEX_ENTRIES > 0)); then step "remove autorelabel's entries from Vagrant's machine index" vagrant_index remove; fi
# Let the private profile's VBoxSVC exit before its directory is deleted.
[[ -n "$VBOX_PRIVATE" ]] && quiet vbox_wait none private

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
  for prof in $(vbox_profiles); do
    [[ "$prof" == private && ! -d "$VBOX_PRIVATE" ]] && continue
    while read -r x; do [[ -n "$x" ]] && LEFT+=("VirtualBox VM $x ($(vbox_label "$prof"))"); done \
      < <(vbm "$prof" list vms 2>/dev/null | sed -n "s/^\"\(${PREFIX}-[^\"]*\)\".*/\1/p")
  done
fi
if ((HAVE_VAGRANT)) && ((KEEP_BOX == 0)) && vagrant box list 2>/dev/null | grep -q "^${BOX} "; then LEFT+=("Vagrant box $BOX"); fi
left_index="$(vagrant_index count 2>/dev/null || echo 0)"
((left_index > 0)) && LEFT+=("$left_index entries in Vagrant's machine index (vagrant global-status)")
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
if [[ -z "$REPO" ]] && ((HAVE_VAGRANT)); then
  echo "${D}Without the repository, Vagrant's machine index may still list the lab VMs. To clear every${O}"
  echo "${D}deleted machine from it (other projects' too): vagrant global-status --prune${O}"
fi
if [[ -n "$ISO_PATH" && -f "$ISO_PATH" ]]; then echo "${D}Your ISO was kept: $ISO_PATH${O}"; fi
# libvirt keeps each VM's QEMU log (root-owned) after the VM is deleted; removing it needs root.
if compgen -G "/var/log/libvirt/qemu/${PREFIX}-*.log" >/dev/null; then
  echo "${D}libvirt kept its logs of the lab VMs (root-owned, about 1 MB each). To remove them too:${O}"
  echo "${D}  sudo rm -f /var/log/libvirt/qemu/${PREFIX}-*.log*${O}"
fi
if ((${#USER_UNDO[@]})); then
  echo; echo "${B}Steps you ran yourself during setup (undo them only if you want to):${O}"
  printf '  %s\n' "${USER_UNDO[@]}"
fi
exit "$STATUS"
