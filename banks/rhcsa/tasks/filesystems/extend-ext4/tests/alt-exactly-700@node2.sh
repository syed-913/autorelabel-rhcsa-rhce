#!/usr/bin/env bash
# Exactly the size asked for: an ext4 of 700 MiB, which df shows as about 646 (journal, inode tables).
p="$(ar_new_partition "$LAB_NODE2_DISK1" 600 lvm)"
pvcreate -q "$p"; vgextend -q "$P_VG" "$p"
lvextend -q -r -L 700M "$P_VG/homelv"
