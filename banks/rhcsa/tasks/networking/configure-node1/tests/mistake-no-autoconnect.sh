#!/usr/bin/env bash
# Common mistake: correct profile, but it does not start at boot.
nic="$(ar_lab_nic)"
nmcli connection add type ethernet con-name "$nic" ifname "$nic" \
  ipv4.method manual ipv4.addresses "$LAB_NODE1_IP/$LAB_PREFIX" \
  ipv4.gateway "$LAB_GATEWAY" ipv4.dns "$LAB_DNS" connection.autoconnect no
nmcli connection up "$nic"
hostnamectl set-hostname "$LAB_NODE1_FQDN"
