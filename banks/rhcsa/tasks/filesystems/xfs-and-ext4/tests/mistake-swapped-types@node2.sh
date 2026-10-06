#!/usr/bin/env bash
# Common mistake: file system types swapped between the mount points.
p1="$(ar_new_partition "$LAB_NODE2_DISK1" 400)"; p2="$(ar_new_partition "$LAB_NODE2_DISK1" 300)"
mkfs.ext4 -q "$p1"; mkfs.xfs -q -f "$p2"
mkdir -p "/srv/$P_WORD-xfs" "/srv/$P_WORD-ext4"
echo "$p1 /srv/$P_WORD-xfs ext4 defaults 0 0" >> /etc/fstab
echo "$p2 /srv/$P_WORD-ext4 xfs defaults 0 0" >> /etc/fstab
systemctl daemon-reload; mount -a
