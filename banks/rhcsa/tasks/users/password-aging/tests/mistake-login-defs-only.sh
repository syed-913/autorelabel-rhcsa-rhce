#!/usr/bin/env bash
# Common mistake: expecting login.defs to change an existing account.
sed -i "s/^PASS_MAX_DAYS.*/PASS_MAX_DAYS\t$P_MAXDAYS/" /etc/login.defs
chage -E "$P_EXPIRE" -d 0 "$P_USER"
