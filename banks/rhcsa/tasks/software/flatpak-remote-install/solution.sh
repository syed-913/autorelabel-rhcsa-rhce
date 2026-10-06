#!/usr/bin/env bash
dnf -y -q install flatpak
flatpak remote-add --system --if-not-exists "$P_REMOTE" "$LAB_FLATPAK_REPOFILE"
flatpak install -y --system --noninteractive "$P_REMOTE" org.mozilla.firefox >/dev/null
