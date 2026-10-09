#!/usr/bin/env bash
# Common mistake: plain cp (copies get root ownership and new timestamps).
mkdir -p "/root/$P_USER-files"
# find exits 1 when it meets unreadable or vanishing entries (/proc, /run); that's expected
find / -user "$P_USER" -type f -not -path '/proc/*' -exec cp {} "/root/$P_USER-files/" \; 2>/dev/null || true
