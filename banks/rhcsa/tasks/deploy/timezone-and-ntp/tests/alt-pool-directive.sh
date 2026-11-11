#!/usr/bin/env bash
# The default pool line edited in place: still a "pool" directive, now naming the lab server
# (which has an IPv4 and an IPv6 address, so chronyd may list both).
timedatectl set-timezone "$P_TZ"
sed -i "s/^pool .*/pool $LAB_NTP_SERVER iburst/" /etc/chrony.conf
systemctl enable chronyd; systemctl restart chronyd
timedatectl set-ntp true
