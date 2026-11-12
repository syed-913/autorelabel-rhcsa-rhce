#!/usr/bin/env bash
# What a keyword search finds on this system as the exam starts, for the check: software
# installed later adds manual pages.
mkdir -p /etc/autorelabel
mandb -q
man -k "$P_KEYWORD" | LC_ALL=C sort > "/etc/autorelabel/man-$P_KEYWORD.expected"
# A fresh system: the man index has not been built yet.
rm -rf /var/cache/man/* 2>/dev/null || true
