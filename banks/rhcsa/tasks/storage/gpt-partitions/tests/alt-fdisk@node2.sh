#!/usr/bin/env bash
# Valid alternative: fdisk (scripted keystrokes).
disk="$LAB_NODE2_DISK1"
obsolete="$(lsblk -nbrpo NAME,SIZE,TYPE "$disk" | awk '$3=="part" && int($2/1048576)==256 {print $1}')"
num="${obsolete##*[!0-9]}"
printf 'd\n%s\nn\n\n\n+%sM\nn\n\n\n+%sM\nw\n' "$num" "$P_SIZE1" "$P_SIZE2" | fdisk "$disk" >/dev/null 2>&1 || true
partprobe "$disk"; udevadm settle
