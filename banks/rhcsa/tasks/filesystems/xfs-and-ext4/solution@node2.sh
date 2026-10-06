#!/usr/bin/env bash
p1="$(ar_new_partition "$LAB_NODE2_DISK1" 400)"; p2="$(ar_new_partition "$LAB_NODE2_DISK1" 300)"
mkfs.xfs -q "$p1"; mkfs.ext4 -q "$p2"
mkdir -p "/srv/$P_WORD-xfs" "/srv/$P_WORD-ext4"
echo "UUID=$(blkid -s UUID -o value "$p1") /srv/$P_WORD-xfs xfs defaults 0 0" >> /etc/fstab
echo "UUID=$(blkid -s UUID -o value "$p2") /srv/$P_WORD-ext4 ext4 defaults 0 2" >> /etc/fstab
systemctl daemon-reload; mount -a
