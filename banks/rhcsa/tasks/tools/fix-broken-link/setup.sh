#!/usr/bin/env bash
b="/opt/$P_WORD"; mkdir -p "$b/releases/1.0" "$b/releases/2.0" "$b/current" "$b/backup"
for f in app.bin settings.conf; do echo "2.0 $f" > "$b/releases/2.0/$f"; done
echo "1.0 readme" > "$b/releases/1.0/README"
ln -sfn "$b/releases/1.0/README" "$b/current/README"
ln -sfn "$b/releases/1.0/app.bin" "$b/current/app.bin"        # dangling: 1.0/app.bin was removed
ln -sfn "$b/releases/2.0/settings.conf" "$b/current/settings.conf"
