#!/usr/bin/env bash
p="$(ar_new_partition "$LAB_NODE2_DISK1" 600 lvm)"
vgextend -q "$P_VG" "$p"
lvextend -q -L 720M "$P_VG/homelv"
