#!/usr/bin/env bash
# Common mistake: > instead of >> for the summary (overwrites the first output).
lab-inventory > /root/inventory.out 2> /root/inventory.err
lab-inventory --summary > /root/inventory.out
lab-inventory --verbose > /root/inventory.all 2>&1
lab-inventory 2>/dev/null | grep -c disk > /root/disk-count.txt
