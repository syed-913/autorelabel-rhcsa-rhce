#!/usr/bin/env bash
# Valid alternative: one line per key in the map, entry in /etc/auto.master.
dnf -y -q install autofs nfs-utils
echo "/projects /etc/auto.projects" >> /etc/auto.master
for p in alpha beta gamma; do echo "$p -rw $LAB_NFS_SERVER:/exports/projects/$p"; done > /etc/auto.projects
systemctl enable --now autofs; systemctl restart autofs
