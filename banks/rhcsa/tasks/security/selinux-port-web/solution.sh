#!/usr/bin/env bash
semanage port -a -t http_port_t -p tcp "$P_PORT"
firewall-cmd --permanent --add-port="$P_PORT/tcp"
firewall-cmd --reload
systemctl enable --now httpd
