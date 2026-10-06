#!/usr/bin/env bash
# Common mistake: keeping gpgcheck=1 in the repo and forcing the update with --nogpgcheck.
printf '[extras]\nname=extras\nbaseurl=http://%s/extras/\n' "$LAB_UTILITY_FQDN" > /etc/yum.repos.d/extras.repo
dnf -y -q --nogpgcheck upgrade labtools
