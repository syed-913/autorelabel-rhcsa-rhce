#!/usr/bin/env bash
echo "root:$P_NEW_PASSWORD" | chpasswd
chage -E -1 root
