#!/usr/bin/env bash
# Common mistake: starting atd but not enabling it.
dnf -y -q install at
systemctl start atd
when="$(date -d "$P_DATE" '+%H:%M %Y-%m-%d')"
echo "/usr/bin/logger -t $P_WORD \"one-time job\"" | at "$when" 2>/dev/null
