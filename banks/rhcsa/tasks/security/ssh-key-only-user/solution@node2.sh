#!/usr/bin/env bash
printf 'Match User %s\n    PasswordAuthentication no\n' "$P_USER" > "/etc/ssh/sshd_config.d/50-$P_USER-keys-only.conf"
sshd -t && systemctl reload sshd
