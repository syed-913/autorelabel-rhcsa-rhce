#!/usr/bin/env bash
# Reference solution (what a candidate types on the console).
nic="$(ar_lab_nic)"
nmcli connection add type ethernet con-name "$nic" ifname "$nic" \
  ipv4.method manual ipv4.addresses "$LAB_NODE1_IP/$LAB_PREFIX" \
  ipv4.gateway "$LAB_GATEWAY" ipv4.dns "$LAB_DNS" connection.autoconnect yes
nmcli connection up "$nic"
hostnamectl set-hostname "$LAB_NODE1_FQDN"
