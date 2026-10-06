#!/usr/bin/env bash
nic="$(ar_lab_nic)"; con="$(nmcli -g GENERAL.CONNECTION device show "$nic")"
nmcli connection modify "$con" ipv4.dns "" ipv4.dns-search ""
nmcli connection up "$con" >/dev/null
