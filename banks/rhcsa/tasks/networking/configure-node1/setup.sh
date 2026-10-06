#!/usr/bin/env bash
# Start state: no profile for the lab NIC, no address, default hostname.
# (mgmt0, the grader's interface, is left alone.)
nic="$(ar_lab_nic)"
for f in /etc/NetworkManager/system-connections/*.nmconnection; do
  [[ -e "$f" ]] || continue
  [[ "$(basename "$f")" == "mgmt0.nmconnection" ]] && continue
  rm -f "$f"
done
nmcli connection reload
nmcli device disconnect "$nic" >/dev/null 2>&1 || true
ip addr flush dev "$nic"
hostnamectl set-hostname localhost.localdomain
