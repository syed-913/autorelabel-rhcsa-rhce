#!/usr/bin/env bash
# Common mistake: adding nofail hides the problem (boots, but nothing is mounted).
mount -o remount,rw /
sed -i "s| /$P_MNT ext4 defaults | /$P_MNT ext4 defaults,nofail |" /etc/fstab
systemctl daemon-reload
