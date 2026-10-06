#!/usr/bin/env bash
d="/srv/$P_WORD-logs"; mkdir -p "$d"
for f in app db old; do for i in $(seq 1 200); do echo "$f $P_WORD line $i"; done > "$d/$f.log"; done
install -d /etc/autorelabel
for f in app db old; do sha256sum < "$d/$f.log" | cut -d' ' -f1; done > "/etc/autorelabel/$P_WORD-logs.sums"
gzip "$d/old.log"
