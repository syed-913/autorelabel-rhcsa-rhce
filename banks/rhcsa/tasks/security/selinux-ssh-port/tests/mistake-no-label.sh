#!/usr/bin/env bash
# Common mistake: forgetting the SELinux port type (sshd cannot bind the new port).
printf 'Port 22\nPort %s\n' "$P_PORT" > /etc/ssh/sshd_config.d/60-extra-port.conf
firewall-cmd --permanent --add-port="$P_PORT/tcp"; firewall-cmd --reload
systemctl restart sshd || true
