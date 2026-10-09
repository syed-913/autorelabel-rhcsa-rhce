#!/usr/bin/env bash
# Common mistake: keeping the originals (-k) and leaving extra files behind.
cd "/srv/$P_WORD-logs" || exit 1
gzip -k app.log
bzip2 -k db.log
gunzip -k old.log.gz
