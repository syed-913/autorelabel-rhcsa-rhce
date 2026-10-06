#!/usr/bin/env bash
# Valid alternative: passwd -e to force the change, passwd -x/-w for aging.
passwd -x "$P_MAXDAYS" -w "$P_WARN" "$P_USER" >/dev/null
usermod -e "$P_EXPIRE" "$P_USER"
passwd -e "$P_USER" >/dev/null
sed -i "s/^PASS_MAX_DAYS.*/PASS_MAX_DAYS $P_DEFMAX/" /etc/login.defs
