#!/usr/bin/env bash
# Common mistake: writing the full context instead of just the type.
{
  ps -C "$P_PROCESS" -o label= | head -1
  stat -c %C "$P_PATH"
} > /root/selinux-report.txt
