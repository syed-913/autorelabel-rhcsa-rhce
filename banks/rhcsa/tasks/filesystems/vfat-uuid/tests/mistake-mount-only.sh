#!/usr/bin/env bash
dnf -y -q install dosfstools
part="$(ar_new_partition "$LAB_NODE1_DISK1" 300)"
mkfs.vfat "$part" >/dev/null; mkdir -p "/mnt/$P_DIR"; mount "$part" "/mnt/$P_DIR"
