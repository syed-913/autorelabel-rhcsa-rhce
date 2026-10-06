#!/usr/bin/env bash
usermod -aG "$P_GROUP" "$P_ADMIN"
cat > /etc/sudoers.d/lab-access <<SUDO
%$P_GROUP ALL=(ALL) ALL
$P_OPERATOR ALL=(root) NOPASSWD: /usr/bin/systemctl restart chronyd
SUDO
chmod 0440 /etc/sudoers.d/lab-access
visudo -c -q
