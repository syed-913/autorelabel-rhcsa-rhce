#!/usr/bin/env bash
lvcreate -q -y -L "${P_SIZE}M" -n swaplv "$P_VG"
mkswap -q "/dev/$P_VG/swaplv"; swapon "/dev/$P_VG/swaplv"
