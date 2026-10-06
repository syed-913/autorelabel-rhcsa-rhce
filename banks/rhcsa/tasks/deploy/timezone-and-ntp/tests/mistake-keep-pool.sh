#!/usr/bin/env bash
timedatectl set-timezone "$P_TZ"
echo "server $LAB_NTP_SERVER iburst" >> /etc/chrony.conf
systemctl restart chronyd
