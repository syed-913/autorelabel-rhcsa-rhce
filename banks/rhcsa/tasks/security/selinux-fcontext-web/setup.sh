#!/usr/bin/env bash
ar_install httpd
install -d -m 0755 "/srv/$P_SITE"
echo "AR-$P_TOKEN welcome to $P_SITE" > "/srv/$P_SITE/index.html"
cat > "/etc/httpd/conf.d/$P_SITE.conf" <<CONF
DocumentRoot "/srv/$P_SITE"
<Directory "/srv/$P_SITE">
    AllowOverride None
    Require all granted
</Directory>
CONF
restorecon -R "/srv/$P_SITE"      # default label for /srv: not readable by httpd
systemctl enable --now httpd
