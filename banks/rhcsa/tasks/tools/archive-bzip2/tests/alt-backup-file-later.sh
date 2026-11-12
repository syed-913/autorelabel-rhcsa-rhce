#!/usr/bin/env bash
# The archive is made first; later in the exam a file in that directory gets a backup copy
# (as before editing a configuration file for another task).
tar -cjf "/root/$P_NAME-backup.tar.bz2" "$P_DIR" 2>/dev/null
f="$(find "$P_DIR" -maxdepth 1 -type f | sort | sed -n 1p)"
cp -p "$f" "$f.bak"
