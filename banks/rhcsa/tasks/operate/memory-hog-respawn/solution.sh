#!/usr/bin/env bash
ps -eo comm --sort=-rss | sed -n 2p > /root/memory-hog.txt
# The respawning cron entry (grep exits non-zero when a glob such as /var/spool/cron/* matches nothing)
files="$(grep -ls "$P_WORD-cache" /etc/cron.d/* /var/spool/cron/* || true)"
if [ -n "$files" ]; then rm -f $files; fi
pkill -x "$P_WORD-cache" || true
