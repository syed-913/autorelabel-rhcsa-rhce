#!/usr/bin/env bash
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=persistent\nSystemMaxUse=%sM\n' "$P_SIZE" > /etc/systemd/journald.conf.d/lab.conf
systemctl restart systemd-journald
