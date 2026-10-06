#!/usr/bin/env bash
# Common mistake: removing the LV but leaving its fstab line (next boot: emergency mode).
umount /scratch
lvremove -q -y "$P_VG/scratch"
