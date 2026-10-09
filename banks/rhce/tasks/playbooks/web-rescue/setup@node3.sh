#!/usr/bin/env bash
# The "legacy" web server: a configuration httpd refuses to start with.
ar_install httpd
printf '# legacy virtual host (broken)\nListen 80\nServerLimiet 10\n' > /etc/httpd/conf.d/zz-legacy.conf
restorecon /etc/httpd/conf.d/zz-legacy.conf
