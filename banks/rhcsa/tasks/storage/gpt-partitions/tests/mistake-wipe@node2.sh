#!/usr/bin/env bash
# Common mistake: a new partition table (mklabel) wipes the data partition.
disk="$LAB_NODE2_DISK1"
umount "/mnt/keep-$P_WORD" 2>/dev/null || true
parted -s "$disk" mklabel gpt mkpart a 1MiB "$((P_SIZE1 + 1))MiB" mkpart b "$((P_SIZE1 + 1))MiB" "$((P_SIZE1 + P_SIZE2 + 1))MiB"
partprobe "$disk"
