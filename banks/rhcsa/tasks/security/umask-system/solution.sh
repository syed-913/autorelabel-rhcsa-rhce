#!/usr/bin/env bash
cat > /etc/profile.d/umask-users.sh <<'SH'
# Regular users get umask 027 (root keeps the default)
if [ "$(id -u)" -ge 1000 ]; then
    umask 027
fi
SH
