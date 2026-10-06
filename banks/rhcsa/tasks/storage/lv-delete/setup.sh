#!/usr/bin/env bash
p="$(ar_new_partition "$LAB_NODE1_DISK1" 512 lvm)"
pvcreate -q "$p"; vgcreate -q "$P_VG" "$p"
lvcreate -q -y -L 200M -n scratch "$P_VG"; mkfs.ext4 -q "/dev/$P_VG/scratch"
mkdir -p /scratch; echo "/dev/$P_VG/scratch /scratch ext4 defaults 0 2" >> /etc/fstab
systemctl daemon-reload; mount /scratch; echo temp > /scratch/old.txt
