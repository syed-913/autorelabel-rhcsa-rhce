#!/usr/bin/env bash
p="$(ar_new_partition "$LAB_NODE2_DISK1" 500 lvm)"
pvcreate -q "$p"; vgextend -q "$P_VG" "$p"
