#!/usr/bin/env bash
# Common mistake: firewall rule without --permanent (gone after the reboot).
semanage port -a -t http_port_t -p tcp "$P_PORT"
firewall-cmd --add-port="$P_PORT/tcp"
systemctl enable --now httpd
