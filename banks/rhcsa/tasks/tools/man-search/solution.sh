#!/usr/bin/env bash
mandb -q
man -k "$P_KEYWORD" > "/root/man-$P_KEYWORD.txt"
echo 5 > /root/man-section.txt
