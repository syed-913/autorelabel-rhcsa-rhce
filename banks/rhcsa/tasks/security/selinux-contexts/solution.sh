#!/usr/bin/env bash
{
  ps -C "$P_PROCESS" -o label= | head -1 | cut -d: -f3
  stat -c %C "$P_PATH" | cut -d: -f3
} > /root/selinux-report.txt
