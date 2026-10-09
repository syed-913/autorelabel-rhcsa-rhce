#!/usr/bin/env bash
# The connection profile bound to the lab interface (not the first or last one listed).
nic="$(ar_lab_nic)"
con=""
while IFS= read -r c; do
  if [ "$(nmcli -g connection.interface-name connection show "$c")" = "$nic" ]; then con="$c"; fi
done < <(nmcli -g NAME connection show)
nmcli connection modify "$con" connection.autoconnect yes
nmcli connection up "$con" >/dev/null || true
