#!/usr/bin/env bash
# Common mistake: --user installs land in root's home, not system-wide.
dnf -y -q install flatpak
flatpak remote-add --user --if-not-exists "$P_REMOTE" "$LAB_FLATPAK_REPOFILE"
flatpak install -y --user --noninteractive "$P_REMOTE" org.mozilla.firefox >/dev/null
