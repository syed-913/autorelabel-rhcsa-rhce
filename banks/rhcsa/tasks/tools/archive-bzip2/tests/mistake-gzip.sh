#!/usr/bin/env bash
# Common mistake: gzip compression with a .bz2 name.
tar -czf "/root/$P_NAME-backup.tar.bz2" "$P_DIR" 2>/dev/null
