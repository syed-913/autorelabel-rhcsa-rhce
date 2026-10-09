#!/usr/bin/env bash
install -d -o student -g student /home/student/scripts
cat > /home/student/scripts/check-hosts.sh <<'SH'
#!/bin/bash
# check-hosts.sh FILE - report whether each host name listed in FILE resolves
if [ $# -gt 1 ]; then
  echo "usage: $0 FILE" >&2
  exit 2
fi
while read host; do
  if getent hosts "$host" > /dev/null; then
    echo "$host down"
  else
    echo "$host up"
  fi
done < "$2"
SH
chown student:student /home/student/scripts/check-hosts.sh; chmod 0755 /home/student/scripts/check-hosts.sh
