#!/usr/bin/env bash
part="$(ar_new_partition "$LAB_NODE1_DISK2" 1024 lvm)"
pvcreate -q "$part"; vgcreate -q "$P_VG" "$part"
lvcreate -q -y -L 400M -n datalv "$P_VG"; mkfs.xfs -q "/dev/$P_VG/datalv"
mkdir -p "/srv/$P_VG-data"
echo "/dev/$P_VG/datalv /srv/$P_VG-data xfs defaults 0 0" >> /etc/fstab
systemctl daemon-reload; mount "/srv/$P_VG-data"
ar_fill "/srv/$P_VG-data" "$P_VG"
