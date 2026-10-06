#!/usr/bin/env bash
# Common mistake: editing /etc/resolv.conf by hand (NetworkManager rewrites it).
printf 'search lab.example.com\nnameserver %s\n' "$LAB_DNS" > /etc/resolv.conf
hostnamectl set-hostname "$P_SHORT.lab.example.com"
