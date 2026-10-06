#!/usr/bin/env bash
# Common mistake: forgetting -type f, so directories get copied as well.
mkdir -p "/root/$P_USER-files"
find / -user "$P_USER" -not -path '/proc/*' -not -path '/sys/*' -exec cp -rp {} "/root/$P_USER-files/" \; 2>/dev/null
