#!/usr/bin/env bash
ps -eo comm --sort=-rss | sed -n 2p > /root/memory-hog.txt
pkill -9 -x "$P_WORD-cache"
