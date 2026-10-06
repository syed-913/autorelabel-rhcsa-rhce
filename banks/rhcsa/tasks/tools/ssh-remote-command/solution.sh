#!/usr/bin/env bash
# Self-test stand-in for: ssh root@node2 lsblk -o NAME,SIZE,TYPE > /root/node2-disks.txt
{
  echo "NAME   SIZE TYPE"
  echo "vda     20G disk"
  echo "$(basename "$LAB_NODE2_DISK1")      ${LAB_NODE2_DISK1_GB}G disk"
} > /root/node2-disks.txt
