#!/usr/bin/env bash
# The weekly log rotation falls between the work and the grading: the sudo record is then in
# /var/log/secure-<date>, not in /var/log/secure.
su - "$P_USER" -c "echo '$P_PASSWORD' | sudo -S touch /root/$P_WORD-by-sudo" 2>/dev/null
sleep 2
logrotate -f /etc/logrotate.conf      # the whole configuration: its global options name the rotated files
