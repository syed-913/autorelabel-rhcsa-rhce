#!/usr/bin/env bash
# Common mistake: installing the new app but forgetting to remove the old one.
flatpak install -y --system --noninteractive --from "http://$LAB_UTILITY_FQDN/flatpak/org.mozilla.Thunderbird.flatpakref" >/dev/null
