#!/usr/bin/env bash
# Common mistake: copying instead of moving.
mkdir -p "/srv/$P_WORD-archive/2026/q3"
cp "/srv/$P_WORD-inbox/"*.csv "/srv/$P_WORD-archive/2026/q3/"
rm -f "/srv/$P_WORD-inbox/"*.tmp
rmdir "/srv/$P_WORD-inbox/old"
