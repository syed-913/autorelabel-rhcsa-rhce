#!/usr/bin/env bash
ar_install flatpak
flatpak remote-add --system --if-not-exists lab "$LAB_FLATPAK_REPOFILE"
flatpak install -y --system --noninteractive lab org.mozilla.firefox >/dev/null
