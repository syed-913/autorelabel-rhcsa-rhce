#!/usr/bin/env bash
cd "/srv/$P_WORD-logs"
gzip app.log
bzip2 db.log
gunzip old.log.gz
