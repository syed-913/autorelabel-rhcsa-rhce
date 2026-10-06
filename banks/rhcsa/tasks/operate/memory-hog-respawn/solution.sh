#!/usr/bin/env bash
ps -eo comm --sort=-rss | sed -n 2p > /root/memory-hog.txt
grep -l "$P_WORD-cache" /etc/cron.d/* /var/spool/cron/* 2>/dev/null | xargs -r rm -f
pkill -x "$P_WORD-cache" || true
