#!/usr/bin/env bash
# Common mistake: extracting into the current directory instead of using -C.
mkdir -p "/srv/$P_WORD-restore"
(cd /root && tar -xf "/root/$P_WORD-bundle.tar")
tar -czf "/root/$P_WORD-restore.tar.gz" "/srv/$P_WORD-restore" 2>/dev/null
