#!/usr/bin/env bash
chage -M "$P_MAXDAYS" -W "$P_WARN" -E "$P_EXPIRE" "$P_USER"
chage -d 0 "$P_USER"
sed -i "s/^PASS_MAX_DAYS.*/PASS_MAX_DAYS\t$P_DEFMAX/" /etc/login.defs
