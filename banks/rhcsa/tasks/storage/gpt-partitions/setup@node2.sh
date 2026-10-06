#!/usr/bin/env bash
disk="$LAB_NODE2_DISK1"
keep="$(ar_new_partition "$disk" 512)"
ar_new_partition "$disk" 256 >/dev/null
mkfs.ext4 -q -L "keep$P_WORD" "$keep"
mkdir -p "/mnt/keep-$P_WORD"
echo "UUID=$(blkid -s UUID -o value "$keep") /mnt/keep-$P_WORD ext4 defaults 0 2" >> /etc/fstab
systemctl daemon-reload; mount "/mnt/keep-$P_WORD"
ar_fill "/mnt/keep-$P_WORD" "$P_WORD"
