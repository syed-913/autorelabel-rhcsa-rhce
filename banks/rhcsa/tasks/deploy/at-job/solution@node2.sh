#!/usr/bin/env bash
dnf -y -q install at
systemctl enable --now atd
when="$(date -d "$P_DATE" '+%H:%M %Y-%m-%d')"
echo "/usr/bin/logger -t $P_WORD \"one-time job\"" | at "$when" 2>/dev/null
