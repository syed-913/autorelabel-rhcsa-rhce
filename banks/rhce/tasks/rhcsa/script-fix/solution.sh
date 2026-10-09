#!/usr/bin/env bash
cat > /home/student/scripts/check-hosts.sh <<'SH'
#!/bin/bash
# check-hosts.sh FILE - report whether each host name listed in FILE resolves
if [ $# -lt 1 ]; then
  echo "usage: $0 FILE" >&2
  exit 2
fi
while read -r host; do
  if getent hosts "$host" > /dev/null; then
    echo "$host up"
  else
    echo "$host down"
  fi
done < "$1"
SH
