#!/usr/bin/env bash
lvcreate -q -y -L "${P_SIZE}M" -n swaplv "$P_VG"
mkswap -q "/dev/$P_VG/swaplv"
echo "/dev/$P_VG/swaplv none swap defaults 0 0" >> /etc/fstab
systemctl daemon-reload; swapon -a
