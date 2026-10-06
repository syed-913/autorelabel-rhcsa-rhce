#!/usr/bin/env bash
dnf -y -q install dosfstools
part="$(ar_new_partition "$LAB_NODE1_DISK1" 300)"
mkfs.vfat "$part" >/dev/null
mkdir -p "/mnt/$P_DIR"
echo "UUID=$(blkid -s UUID -o value "$part") /mnt/$P_DIR vfat defaults 0 0" >> /etc/fstab
systemctl daemon-reload; mount "/mnt/$P_DIR"
