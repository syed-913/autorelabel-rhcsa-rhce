#!/usr/bin/env bash
# Mounted on first access by systemd (x-systemd.automount in fstab): until something opens the
# directory, only the automount point is there.
dnf -y -q install nfs-utils
mkdir -p "/mnt/$P_SHARE"
echo "$LAB_NFS_SERVER:/exports/$P_SHARE /mnt/$P_SHARE nfs _netdev,x-systemd.automount 0 0" >> /etc/fstab
systemctl daemon-reload; systemctl restart remote-fs.target
