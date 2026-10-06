#!/usr/bin/env bash
dnf -y -q install autofs nfs-utils
echo "/$P_BASE /etc/auto.$P_BASE" > "/etc/auto.master.d/$P_BASE.autofs"
echo "* -rw,sync $LAB_NFS_SERVER:/exports/$P_BASE/&" > "/etc/auto.$P_BASE"
systemctl enable --now autofs; systemctl restart autofs
