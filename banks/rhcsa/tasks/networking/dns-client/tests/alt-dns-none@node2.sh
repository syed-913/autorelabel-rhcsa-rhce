#!/usr/bin/env bash
# Valid alternative: NetworkManager told to leave resolv.conf alone, then a hand-written file.
printf '[main]\ndns=none\n' > /etc/NetworkManager/conf.d/90-dns-none.conf
systemctl reload NetworkManager
printf 'search lab.example.com\nnameserver %s\n' "$LAB_DNS" > /etc/resolv.conf
hostnamectl set-hostname "$P_SHORT.lab.example.com"
