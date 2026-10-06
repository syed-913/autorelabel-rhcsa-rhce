#!/usr/bin/env bash
lab-inventory > /root/inventory.out 2> /root/inventory.err
lab-inventory --summary >> /root/inventory.out
lab-inventory --verbose &> /root/inventory.all
lab-inventory 2>/dev/null | grep disk | wc -l > /root/disk-count.txt
