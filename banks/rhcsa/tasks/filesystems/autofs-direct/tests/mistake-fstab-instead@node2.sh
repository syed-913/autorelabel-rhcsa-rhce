#!/usr/bin/env bash
# Common mistake: a static fstab mount instead of autofs.
dnf -y -q install nfs-utils; mkdir -p "$P_DIR"
echo "$LAB_NFS_SERVER:/exports/direct $P_DIR nfs defaults,_netdev 0 0" >> /etc/fstab
systemctl daemon-reload; mount "$P_DIR"
