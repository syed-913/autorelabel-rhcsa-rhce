#!/usr/bin/env bash
# An existing drop-in with an old value that must be replaced, not duplicated.
printf '# lab tuning\nMaxAuthTries 6\n' > /etc/ssh/sshd_config.d/50-lab.conf
chmod 0600 /etc/ssh/sshd_config.d/50-lab.conf
