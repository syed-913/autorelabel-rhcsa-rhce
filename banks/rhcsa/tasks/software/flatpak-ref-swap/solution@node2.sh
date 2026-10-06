#!/usr/bin/env bash
flatpak uninstall -y --noninteractive org.mozilla.firefox >/dev/null
flatpak install -y --system --noninteractive --from "http://$LAB_UTILITY_FQDN/flatpak/org.mozilla.Thunderbird.flatpakref" >/dev/null
