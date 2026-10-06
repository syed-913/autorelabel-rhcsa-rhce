#!/usr/bin/env bash
p="$(ar_new_partition "$LAB_NODE2_DISK1" 400 lvm)"
pvcreate -q "$p"; vgcreate -q "$P_VG" "$p"
lvcreate -q -y -l 100%FREE -n homelv "$P_VG"; mkfs.ext4 -q "/dev/$P_VG/homelv"
mkdir -p "/srv/$P_VG-home"; echo "/dev/$P_VG/homelv /srv/$P_VG-home ext4 defaults 0 2" >> /etc/fstab
systemctl daemon-reload; mount "/srv/$P_VG-home"; ar_fill "/srv/$P_VG-home" "$P_VG"
