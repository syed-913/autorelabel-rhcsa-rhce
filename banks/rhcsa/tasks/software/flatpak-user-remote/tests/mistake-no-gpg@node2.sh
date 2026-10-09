#!/usr/bin/env bash
# Common mistake: disabling verification instead of importing the key.
dnf -y -q install flatpak
as_user "$P_USER" flatpak remote-add --user --no-gpg-verify "$P_REMOTE" "$LAB_FLATPAK_REPO"
