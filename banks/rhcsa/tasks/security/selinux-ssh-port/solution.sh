#!/usr/bin/env bash
semanage port -a -t ssh_port_t -p tcp "$P_PORT"
printf 'Port 22\nPort %s\n' "$P_PORT" > /etc/ssh/sshd_config.d/60-extra-port.conf
firewall-cmd --permanent --add-port="$P_PORT/tcp"; firewall-cmd --reload
sshd -t && systemctl restart sshd
