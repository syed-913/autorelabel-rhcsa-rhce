#!/usr/bin/env bash
# Typed on the console in emergency mode (root shell):
mount -o remount,rw /
dev="$(lsblk -nrpo NAME,FSTYPE "$LAB_NODE1_DISK1" | awk '$2=="ext4" {print $1}' | tail -1)"
sed -i "s|^UUID=[^ ]* /$P_MNT |UUID=$(blkid -s UUID -o value "$dev") /$P_MNT |" /etc/fstab
systemctl daemon-reload
mount -a
