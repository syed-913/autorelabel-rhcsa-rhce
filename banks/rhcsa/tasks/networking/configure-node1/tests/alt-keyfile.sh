#!/usr/bin/env bash
# Valid alternative: write a NetworkManager keyfile by hand and set /etc/hostname.
nic="$(ar_lab_nic)"
cat > /etc/NetworkManager/system-connections/lab.nmconnection <<EOF
[connection]
id=lab
type=ethernet
interface-name=$nic

[ipv4]
method=manual
address1=$LAB_NODE1_IP/$LAB_PREFIX,$LAB_GATEWAY
dns=$LAB_DNS;

[ipv6]
method=auto
EOF
chmod 600 /etc/NetworkManager/system-connections/lab.nmconnection
nmcli connection reload
nmcli connection up lab
echo "$LAB_NODE1_FQDN" > /etc/hostname
hostname "$LAB_NODE1_FQDN"
