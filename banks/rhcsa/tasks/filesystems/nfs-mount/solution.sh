#!/usr/bin/env bash
dnf -y -q install nfs-utils
mkdir -p "/mnt/$P_SHARE"
echo "$LAB_NFS_SERVER:/exports/$P_SHARE /mnt/$P_SHARE nfs defaults,_netdev 0 0" >> /etc/fstab
systemctl daemon-reload; mount "/mnt/$P_SHARE"
