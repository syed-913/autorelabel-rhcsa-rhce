#!/usr/bin/env bash
# Common mistake: switching signature checking off globally.
sed -i 's/^gpgcheck=.*/gpgcheck=0/' /etc/dnf/dnf.conf
printf '[extras]\nname=extras\nbaseurl=http://%s/extras/\ngpgcheck=0\n' "$LAB_UTILITY_FQDN" > /etc/yum.repos.d/extras.repo
dnf -y -q upgrade labtools
