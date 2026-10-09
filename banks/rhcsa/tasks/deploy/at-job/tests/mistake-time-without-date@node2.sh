#!/usr/bin/env bash
# Common mistake: giving at only the time of day, which means the next occurrence of that time
# (today or tomorrow), not the requested date.
dnf -y -q install at
systemctl enable --now atd
echo "/usr/bin/logger -t $P_WORD \"one-time job\"" | at "$(date -d "$P_DATE" '+%H:%M')" 2>/dev/null
