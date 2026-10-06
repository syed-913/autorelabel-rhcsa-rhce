#!/usr/bin/env bash
chown -R "$P_USER:$P_USER" "/home/$P_USER"
chmod 0700 "/home/$P_USER"
restorecon -R "/home/$P_USER"
