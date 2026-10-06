#!/usr/bin/env bash
p="$(ar_new_partition "$LAB_NODE2_DISK1" 600 lvm)"
pvcreate -q "$p"; vgextend -q "$P_VG" "$p"
lvextend -q -r -L 720M "$P_VG/homelv"
