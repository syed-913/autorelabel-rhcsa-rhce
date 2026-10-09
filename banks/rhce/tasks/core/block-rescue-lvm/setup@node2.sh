#!/usr/bin/env bash
part="$(ar_new_partition "$LAB_NODE2_DISK1" 1024 lvm)"
pvcreate -q "$part"; vgcreate -q research "$part"
