#!/usr/bin/env bash
sed -i 's/^pool /#pool /' /etc/chrony.conf
echo "server $LAB_NTP_SERVER iburst" >> /etc/chrony.conf
systemctl enable --now chronyd
