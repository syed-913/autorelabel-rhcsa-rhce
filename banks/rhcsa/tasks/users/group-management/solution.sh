#!/usr/bin/env bash
groupadd -g "$P_GID" "$P_NEWGROUP"
usermod -aG "$P_NEWGROUP" "$P_U1"; usermod -aG "$P_NEWGROUP" "$P_U2"
gpasswd -d "$P_U2" "$P_OLDGROUP"
groupmod -n "$P_RENAMED" "legacy-$P_RENAMED"
