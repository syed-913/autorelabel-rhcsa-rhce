#!/usr/bin/env bash
# The mount point written as the shell completes it, with a trailing slash.
part="$(ar_new_partition "$LAB_NODE1_DISK1" 500)"
mkfs.ext4 -q -L "$P_LABEL" "$part"
mkdir -p "/mnt/$P_LABEL"
echo "LABEL=$P_LABEL /mnt/$P_LABEL/ ext4 defaults 0 2" >> /etc/fstab
systemctl daemon-reload; mount "/mnt/$P_LABEL"
