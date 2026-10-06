#!/usr/bin/env bash
dnf -y -q install autofs nfs-utils
echo "/projects /etc/auto.projects" > /etc/auto.master.d/projects.autofs
echo "* -rw,sync $LAB_NFS_SERVER:/exports/projects/&" > /etc/auto.projects
systemctl enable --now autofs; systemctl restart autofs
