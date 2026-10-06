#!/usr/bin/env bash
ar_user "$P_USER" "Lab-$RANDOM-pw"
n=0
for dir in /var/tmp /opt /srv /usr/local/share /etc; do
  n=$((n+1))
  f="$dir/.$P_USER-data-$n.dat"; [ $n -gt 2 ] && f="$dir/$P_USER-report-$n.txt"
  echo "data $n for $P_USER" > "$f"
  chown "$P_USER:" "$f"; chmod "0$((n % 2 + 6))40" "$f"
  touch -d "2025-0$n-1$n 1$n:00" "$f"
done
# a directory owned by the user: must not be copied (regular files only)
mkdir -p "/srv/$P_USER-dir"; chown "$P_USER:" "/srv/$P_USER-dir"
