#!/usr/bin/env bash
for c in $(nmcli -g NAME connection show); do [ "$c" = mgmt0 ] || con="$c"; done
nmcli connection up "$con" >/dev/null || true
