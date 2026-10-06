#!/usr/bin/env bash
# Common mistake: mounting by UUID when the task asked for the label.
part="$(ar_new_partition "$LAB_NODE1_DISK1" 500)"
mkfs.ext4 -q -L "$P_LABEL" "$part"; mkdir -p "/mnt/$P_LABEL"
echo "UUID=$(blkid -s UUID -o value "$part") /mnt/$P_LABEL ext4 defaults 0 2" >> /etc/fstab
systemctl daemon-reload; mount "/mnt/$P_LABEL"
