#!/usr/bin/env bash
# Common mistake: running lsblk locally on node1.
lsblk -o NAME,SIZE,TYPE > /root/node2-disks.txt
