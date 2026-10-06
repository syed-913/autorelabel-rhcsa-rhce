#!/usr/bin/env bash
p="$(ar_new_partition "$LAB_NODE2_DISK1" 600 lvm)"
vgextend -q "$P_VG" "$p"
lvextend -q -l +100%FREE "$P_VG/homelv"
resize2fs "/dev/$P_VG/homelv" >/dev/null 2>&1
