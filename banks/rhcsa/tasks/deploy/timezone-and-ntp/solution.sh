#!/usr/bin/env bash
timedatectl set-timezone "$P_TZ"
sed -i 's/^pool /#pool /' /etc/chrony.conf
echo "server $LAB_NTP_SERVER iburst" >> /etc/chrony.conf
systemctl enable chronyd; systemctl restart chronyd
timedatectl set-ntp true
