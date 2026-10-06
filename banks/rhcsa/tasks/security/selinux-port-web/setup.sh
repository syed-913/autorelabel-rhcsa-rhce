#!/usr/bin/env bash
ar_install httpd
echo "AR-$P_TOKEN node2 web site" > /var/www/html/index.html
restorecon -R /var/www/html
sed -i "s/^Listen .*/Listen $P_PORT/" /etc/httpd/conf/httpd.conf
systemctl disable --now httpd >/dev/null 2>&1 || true
systemctl start httpd >/dev/null 2>&1 || true   # fails: SELinux denies binding the port
