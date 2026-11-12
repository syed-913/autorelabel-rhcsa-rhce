#!/usr/bin/env bash
# Common mistake: searching before the index exists (saves "nothing appropriate").
# Installing a package builds the index in the background (man-db's file trigger), and
# another task's solution may just have done that: let it finish, then start without one.
while systemctl is-active --quiet man-db-cache-update.service; do sleep 1; done
find /var/cache/man -name index.db -delete
man -k "$P_KEYWORD" > "/root/man-$P_KEYWORD.txt" 2>&1 || true   # exits 16: nothing found
echo 5 > /root/man-section.txt
