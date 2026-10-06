#!/usr/bin/env bash
dnf -y -q install flatpak
sudo -u "$P_USER" -H bash -c "curl -fsSo /tmp/lab-$P_USER.gpg http://$LAB_UTILITY_FQDN/flatpak/lab.gpg && \
  flatpak remote-add --user --gpg-import=/tmp/lab-$P_USER.gpg $P_REMOTE $LAB_FLATPAK_REPO"
