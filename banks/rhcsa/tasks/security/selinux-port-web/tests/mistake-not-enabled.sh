#!/usr/bin/env bash
# Common mistake: started, but not enabled at boot.
semanage port -a -t http_port_t -p tcp "$P_PORT"
firewall-cmd --permanent --add-port="$P_PORT/tcp"
firewall-cmd --reload
systemctl start httpd
