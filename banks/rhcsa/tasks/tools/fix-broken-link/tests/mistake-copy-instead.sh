#!/usr/bin/env bash
b="/opt/$P_WORD"
for l in $(find "$b/current" -xtype l); do ln -sfn "$b/releases/2.0/$(basename "$l")" "$l"; done
cp "$b/releases/2.0/settings.conf" "$b/backup/settings.conf"
