#!/usr/bin/env bash
# Common mistake: writing the full context instead of just the type.
labels="$(ps -C "$P_PROCESS" -o label=)"
{
  head -1 <<<"$labels"
  stat -c %C "$P_PATH"
} > /root/selinux-report.txt
