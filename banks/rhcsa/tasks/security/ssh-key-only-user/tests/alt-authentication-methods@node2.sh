#!/usr/bin/env bash
# Only public keys may authenticate this user: a password is refused although
# PasswordAuthentication itself stays on.
printf 'Match User %s\n    AuthenticationMethods publickey\n' "$P_USER" > "/etc/ssh/sshd_config.d/50-$P_USER-keys-only.conf"
sshd -t && systemctl reload sshd
