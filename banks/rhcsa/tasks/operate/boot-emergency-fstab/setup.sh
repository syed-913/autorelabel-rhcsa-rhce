#!/usr/bin/env bash
part="$(ar_new_partition "$LAB_NODE1_DISK1" 300)"
mkfs.ext4 -q "$part"
mkdir -p "/$P_MNT"
uuid="$(blkid -s UUID -o value "$part")"
# One wrong character in the UUID: the device never appears, systemd gives up → emergency mode.
bad="$(echo "$uuid" | sed 's/^\(.\{7\}\)\(.\)/\1X/' | tr 'X' "$( [ "${uuid:7:1}" = 0 ] && echo 1 || echo 0)")"
echo "UUID=$bad /$P_MNT ext4 defaults 0 2" >> /etc/fstab
systemctl daemon-reload
