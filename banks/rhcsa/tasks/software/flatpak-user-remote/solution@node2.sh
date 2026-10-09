#!/usr/bin/env bash
dnf -y -q install flatpak
as_user "$P_USER" curl -fsSo "/tmp/lab-$P_USER.gpg" "http://$LAB_UTILITY_FQDN/flatpak/lab.gpg"
as_user "$P_USER" flatpak remote-add --user --gpg-import="/tmp/lab-$P_USER.gpg" "$P_REMOTE" "$LAB_FLATPAK_REPO"
