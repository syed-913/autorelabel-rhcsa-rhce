#!/usr/bin/env bash
# Common mistake: swapon without an fstab entry (gone after reboot).
part="$(ar_new_partition "$LAB_NODE2_DISK1" "$P_SIZE" swap)"
mkswap -q "$part"; swapon "$part"
