#!/usr/bin/env bash
# UIDs are agreed with node1's setup through a deterministic choice from the user names.
uid_of() { echo $((5100 + $(echo -n "$1" | cksum | cut -d' ' -f1) % 400)); }
uid1="$(uid_of "$P_USER1")"; uid2="$(uid_of "$P_USER2")"; [ "$uid1" = "$uid2" ] && uid2=$((uid2 + 500))
for pair in "$P_USER1:$uid1" "$P_USER2:$uid2"; do
  u="${pair%%:*}"; id="${pair##*:}"
  install -d -m 0700 "/exports/$P_BASE/$u"
  echo "Welcome home, $u." > "/exports/$P_BASE/$u/welcome.txt"
  chown -R "$id:$id" "/exports/$P_BASE/$u"
done
echo "/exports/$P_BASE $LAB_NETWORK(rw,sync)" > "/etc/exports.d/$P_BASE.exports"
exportfs -ra
