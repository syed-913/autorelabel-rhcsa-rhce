#!/usr/bin/env bash
echo "root:Lab-$RANDOM-$RANDOM" | chpasswd
chage -E 0 root
