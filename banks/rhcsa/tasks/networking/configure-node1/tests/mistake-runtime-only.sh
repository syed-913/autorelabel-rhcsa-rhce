#!/usr/bin/env bash
# Common mistake: runtime-only commands. Everything works until the reboot.
nic="$(ar_lab_nic)"
ip link set "$nic" up
ip addr add "$LAB_NODE1_IP/$LAB_PREFIX" dev "$nic"
ip route add default via "$LAB_GATEWAY" || true
echo "nameserver $LAB_DNS" > /etc/resolv.conf
hostname "$LAB_NODE1_FQDN"
