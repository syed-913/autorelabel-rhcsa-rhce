#!/usr/bin/env bash
disk="$LAB_NODE2_DISK1"
obsolete="$(lsblk -nbrpo NAME,SIZE,TYPE "$disk" | awk '$3=="part" && int($2/1048576)==256 {print $1}')"
num="${obsolete##*[!0-9]}"
parted -s "$disk" rm "$num"
end="$(parted -s "$disk" unit MiB print | awk '/^ *[0-9]+ / {e=$3} END {gsub("MiB","",e); print e}')"
parted -s "$disk" mkpart data1 "${end}MiB" "$((${end%.*} + P_SIZE1 + 1))MiB"
end2="$((${end%.*} + P_SIZE1 + 1))"
parted -s "$disk" mkpart data2 "${end2}MiB" "$((end2 + P_SIZE2))MiB"
partprobe "$disk"; udevadm settle
