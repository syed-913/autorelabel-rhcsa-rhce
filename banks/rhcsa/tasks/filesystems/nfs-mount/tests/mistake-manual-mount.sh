#!/usr/bin/env bash
dnf -y -q install nfs-utils; mkdir -p "/mnt/$P_SHARE"
mount -t nfs "$LAB_NFS_SERVER:/exports/$P_SHARE" "/mnt/$P_SHARE"
