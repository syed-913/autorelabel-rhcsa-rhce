#!/usr/bin/env bash
cd "/srv/$P_WORD-logs" || exit 1
gzip app.log
bzip2 db.log
gunzip old.log.gz
