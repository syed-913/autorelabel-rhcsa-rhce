#!/usr/bin/env bash
b="/opt/$P_WORD"
find "$b/current" -xtype l -print0 | while IFS= read -r -d '' l; do
  ln -sfn "$b/releases/2.0/$(basename "$l")" "$l"
done
ln "$b/releases/2.0/settings.conf" "$b/backup/settings.conf"
