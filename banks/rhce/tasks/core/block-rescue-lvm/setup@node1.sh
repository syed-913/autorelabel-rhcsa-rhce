#!/usr/bin/env bash
part="$(ar_new_partition "$LAB_NODE1_DISK1" 2048 lvm)"
pvcreate -q "$part"; vgcreate -q research "$part"
