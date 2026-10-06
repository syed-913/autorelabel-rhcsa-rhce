#!/usr/bin/env bash
mkdir -p "/srv/$P_WORD-restore"
tar -xf "/root/$P_WORD-bundle.tar" -C "/srv/$P_WORD-restore"
tar -czf "/root/$P_WORD-restore.tar.gz" "/srv/$P_WORD-restore" 2>/dev/null
