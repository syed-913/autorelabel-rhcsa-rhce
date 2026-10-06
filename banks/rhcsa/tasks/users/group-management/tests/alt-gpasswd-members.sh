#!/usr/bin/env bash
groupadd -g "$P_GID" "$P_NEWGROUP"
gpasswd -M "$P_U1,$P_U2" "$P_NEWGROUP"
gpasswd -d "$P_U2" "$P_OLDGROUP"
groupmod -n "$P_RENAMED" "legacy-$P_RENAMED"
