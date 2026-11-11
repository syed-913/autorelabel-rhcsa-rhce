#!/usr/bin/env bash
# Rules without a "run as" list: sudo then runs commands as root only, which is what was asked.
usermod -aG "$P_GROUP" "$P_ADMIN"
cat > /etc/sudoers.d/lab-access <<SUDO
%$P_GROUP ALL=ALL
$P_OPERATOR ALL=NOPASSWD: /usr/bin/systemctl restart chronyd
SUDO
chmod 0440 /etc/sudoers.d/lab-access
visudo -c -q
