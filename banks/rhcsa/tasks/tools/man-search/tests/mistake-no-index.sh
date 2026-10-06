#!/usr/bin/env bash
# Common mistake: searching before the index exists (saves "nothing appropriate").
man -k "$P_KEYWORD" > "/root/man-$P_KEYWORD.txt" 2>&1
echo 5 > /root/man-section.txt
