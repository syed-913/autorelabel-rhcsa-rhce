#!/usr/bin/env bash
# Common mistake: deleting the line (boots, but the file system is no longer mounted).
mount -o remount,rw /
sed -i "\| /$P_MNT |d" /etc/fstab
systemctl daemon-reload
