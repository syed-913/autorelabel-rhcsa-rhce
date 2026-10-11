#!/usr/bin/env bash
labels="$(ps -C "$P_PROCESS" -o label=)"   # not `ps | head`: SIGPIPE under pipefail
{
  head -1 <<<"$labels" | cut -d: -f3
  stat -c %C "$P_PATH" | cut -d: -f3
} > /root/selinux-report.txt
