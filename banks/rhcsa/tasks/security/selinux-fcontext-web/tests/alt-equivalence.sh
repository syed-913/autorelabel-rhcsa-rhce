#!/usr/bin/env bash
# Valid alternative: make /srv/site label like /var/www.
semanage fcontext -a -e /var/www "/srv/$P_SITE"
restorecon -Rv "/srv/$P_SITE"
