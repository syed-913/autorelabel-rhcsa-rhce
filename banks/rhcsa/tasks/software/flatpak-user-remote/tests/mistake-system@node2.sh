#!/usr/bin/env bash
# Common mistake: adding it system-wide as root.
dnf -y -q install flatpak
curl -fsSo /tmp/lab.gpg "http://$LAB_UTILITY_FQDN/flatpak/lab.gpg"
flatpak remote-add --gpg-import=/tmp/lab.gpg "$P_REMOTE" "$LAB_FLATPAK_REPO"
