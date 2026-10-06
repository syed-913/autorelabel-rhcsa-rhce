#!/usr/bin/env bash
part="$(ar_new_partition "$LAB_NODE2_DISK1" "$P_SIZE" swap)"
mkswap -q "$part"
echo "UUID=$(blkid -s UUID -o value "$part") none swap defaults 0 0" >> /etc/fstab
systemctl daemon-reload; swapon -a
