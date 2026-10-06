#!/usr/bin/env bash
# Common mistake: configuring a repository instead (installs 1.1 from the extras repo).
printf '[extras]\nname=extras\nbaseurl=http://%s/extras\ngpgcheck=0\n' "$LAB_UTILITY_FQDN" > /etc/yum.repos.d/extras.repo
dnf -y -q install labtools
