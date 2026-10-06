#!/usr/bin/env bash
# Common mistake: plain cp (copies get root ownership and new timestamps).
mkdir -p "/root/$P_USER-files"
find / -user "$P_USER" -type f -not -path '/proc/*' -exec cp {} "/root/$P_USER-files/" \; 2>/dev/null
