#!/usr/bin/env bash
ps -eo comm --sort=-rss | sed -n 2p > /root/memory-hog.txt
pkill -9 -x "$P_WORD-cache" || true      # it may be between two cron restarts
