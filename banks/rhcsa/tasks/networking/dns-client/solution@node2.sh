#!/usr/bin/env bash
nic="$(ar_lab_nic)"; con="$(nmcli -g GENERAL.CONNECTION device show "$nic")"
nmcli connection modify "$con" ipv4.dns "$LAB_DNS" ipv4.dns-search lab.example.com
nmcli connection up "$con" >/dev/null
hostnamectl set-hostname "$P_SHORT.lab.example.com"
