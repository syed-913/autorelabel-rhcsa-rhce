#!/usr/bin/env bash
p1="$(ar_new_partition "$LAB_NODE1_DISK2" 512 lvm)"
p2="$(ar_new_partition "$LAB_NODE1_DISK2" 512 lvm)"
pvcreate -q "$p1" "$p2"; vgcreate -q "$P_VG" "$p1" "$p2"
lvcreate -q -y -L 300M -n keeplv "$P_VG" "$p1"; mkfs.xfs -q "/dev/$P_VG/keeplv"
mkdir -p "/srv/$P_VG"
echo "/dev/$P_VG/keeplv /srv/$P_VG xfs defaults 0 0" >> /etc/fstab
systemctl daemon-reload; mount "/srv/$P_VG"
ar_fill "/srv/$P_VG" "$P_VG"
echo "$p2" > "/etc/autorelabel/$P_VG-pv2"
