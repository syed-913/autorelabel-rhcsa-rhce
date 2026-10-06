#!/usr/bin/env bash
uid_of() { echo $((5100 + $(echo -n "$1" | cksum | cut -d' ' -f1) % 400)); }
uid1="$(uid_of "$P_USER1")"; uid2="$(uid_of "$P_USER2")"
[ "$uid1" = "$uid2" ] && uid2=$((uid2 + 500))
id "$P_USER1" >/dev/null 2>&1 || useradd -M -d "/$P_BASE/$P_USER1" -u "$uid1" "$P_USER1"
id "$P_USER2" >/dev/null 2>&1 || useradd -M -d "/$P_BASE/$P_USER2" -u "$uid2" "$P_USER2"
echo "$P_USER1:Home-$RANDOM" | chpasswd; echo "$P_USER2:Home-$RANDOM" | chpasswd
install -d /etc/autorelabel
echo "$uid1 $uid2" > "/etc/autorelabel/$P_BASE-uids"
