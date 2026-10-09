#!/usr/bin/env bash
mkdir -p "/root/$P_USER-files"
# find exits 1 when it meets unreadable or vanishing entries (/proc, /run); that's expected
find / -user "$P_USER" -type f -not -path '/proc/*' -not -path '/sys/*' -exec cp -p {} "/root/$P_USER-files/" \; 2>/dev/null || true
