#!/usr/bin/env bash
# Common mistake: configured and started, but not enabled (no time source after reboot).
echo "server $LAB_NTP_SERVER iburst" >> /etc/chrony.conf
systemctl start chronyd
