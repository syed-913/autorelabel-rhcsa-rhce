#!/usr/bin/env bash
# Common mistake: giving the operator full NOPASSWD access.
usermod -aG "$P_GROUP" "$P_ADMIN"
printf '%%%s ALL=(ALL) ALL\n%s ALL=(ALL) NOPASSWD: ALL\n' "$P_GROUP" "$P_OPERATOR" > /etc/sudoers.d/lab-access
chmod 0440 /etc/sudoers.d/lab-access
