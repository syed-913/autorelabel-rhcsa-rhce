#!/usr/bin/env bash
part="$(ar_new_partition "$LAB_NODE1_DISK1" 1024 lvm)"
pvcreate -q "$part"
vgcreate -q -s "${P_PE}M" "$P_VG" "$part"
lvcreate -q -y -l "$P_EXTENTS" -n "$P_LV" "$P_VG"
mkfs.xfs -q "/dev/$P_VG/$P_LV"
mkdir -p "/mnt/$P_LV"
echo "UUID=$(blkid -s UUID -o value "/dev/$P_VG/$P_LV") /mnt/$P_LV xfs defaults 0 0" >> /etc/fstab
systemctl daemon-reload; mount "/mnt/$P_LV"
