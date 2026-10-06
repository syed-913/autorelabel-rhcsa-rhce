#!/usr/bin/env bash
# Common mistake: disabling password logins for everybody.
echo 'PasswordAuthentication no' > /etc/ssh/sshd_config.d/00-nopass.conf
sshd -t && systemctl reload sshd
