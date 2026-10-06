#!/usr/bin/env bash
ar_user "$P_USER" "$P_PASSWORD"
chown -R root:root "/home/$P_USER"
chmod 0755 "/home/$P_USER"
chcon -R -t tmp_t "/home/$P_USER"
