#!/usr/bin/env bash
dnf -y -q install autofs nfs-utils
echo "/- /etc/auto.direct" > /etc/auto.master.d/direct.autofs
echo "$P_DIR -ro $LAB_NFS_SERVER:/exports/direct" > /etc/auto.direct
systemctl enable --now autofs; systemctl restart autofs
