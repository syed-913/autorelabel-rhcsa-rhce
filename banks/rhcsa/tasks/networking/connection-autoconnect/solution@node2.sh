#!/usr/bin/env bash
nic="$(ar_lab_nic)"
con="$(nmcli -g NAME,DEVICE connection show | grep -v '^mgmt0' | head -1 | cut -d: -f1)"
for c in $(nmcli -g NAME connection show); do [ "$c" = mgmt0 ] || con="$c"; done
nmcli connection modify "$con" connection.autoconnect yes
nmcli connection up "$con" >/dev/null || true
