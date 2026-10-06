#!/usr/bin/env bash
# Common mistake: putting the admin in wheel instead of configuring the requested group.
usermod -aG wheel "$P_ADMIN"
echo "$P_OPERATOR ALL=(root) NOPASSWD: /usr/bin/systemctl restart chronyd" > /etc/sudoers.d/lab-access
chmod 0440 /etc/sudoers.d/lab-access
