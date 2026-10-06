#!/usr/bin/env bash
# Common mistake: one line per user instead of a wildcard (works for these two, not "any user").
dnf -y -q install autofs nfs-utils
echo "/$P_BASE /etc/auto.$P_BASE" > "/etc/auto.master.d/$P_BASE.autofs"
for u in "$P_USER1" "$P_USER2"; do echo "$u -rw $LAB_NFS_SERVER:/exports/$P_BASE/$u"; done > "/etc/auto.$P_BASE"
systemctl enable --now autofs; systemctl restart autofs
