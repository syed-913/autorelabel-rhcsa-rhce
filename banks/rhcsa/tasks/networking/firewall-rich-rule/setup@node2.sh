#!/usr/bin/env bash
ar_install httpd
echo "AR-$P_TOKEN restricted site" > /var/www/html/index.html
restorecon -R /var/www/html
systemctl enable --now httpd
firewall-cmd -q --permanent --remove-service=http 2>/dev/null || true
firewall-cmd -q --reload
