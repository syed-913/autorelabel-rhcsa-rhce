#!/usr/bin/env bash
umount /scratch
sed -i '\|[[:space:]]/scratch[[:space:]]|d' /etc/fstab
systemctl daemon-reload
lvremove -q -y "$P_VG/scratch"
