#!/usr/bin/env bash
p="$(ar_new_partition "$LAB_NODE1_DISK2" 1024 lvm)"
pvcreate -q "$p"; vgcreate -q "$P_VG" "$p"
lvcreate -q -y -L 400M -n datalv "$P_VG"; mkfs.xfs -q "/dev/$P_VG/datalv"
mkdir -p "/srv/$P_VG"; echo "/dev/$P_VG/datalv /srv/$P_VG xfs defaults 0 0" >> /etc/fstab
systemctl daemon-reload; mount "/srv/$P_VG"; ar_fill "/srv/$P_VG" "$P_VG"
