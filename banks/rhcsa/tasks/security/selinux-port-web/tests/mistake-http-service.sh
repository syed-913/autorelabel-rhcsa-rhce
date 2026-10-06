#!/usr/bin/env bash
# Common mistake: opening the "http" service (port 80) instead of the custom port.
semanage port -a -t http_port_t -p tcp "$P_PORT"
firewall-cmd --permanent --add-service=http
firewall-cmd --reload
systemctl enable --now httpd
