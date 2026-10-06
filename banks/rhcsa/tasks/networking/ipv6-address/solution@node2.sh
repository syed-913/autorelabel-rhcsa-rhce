#!/usr/bin/env bash
nic="$(ar_lab_nic)"
con="$(nmcli -g GENERAL.CONNECTION device show "$nic")"
nmcli connection modify "$con" +ipv6.addresses "$LAB_IPV6_PREFIX$P_HOST/64"
nmcli connection up "$con" >/dev/null
