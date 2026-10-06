#!/usr/bin/env bash
# Common mistake: deleting and recreating the group instead of renaming it (new GID).
groupadd -g "$P_GID" "$P_NEWGROUP"
usermod -aG "$P_NEWGROUP" "$P_U1"; usermod -aG "$P_NEWGROUP" "$P_U2"
gpasswd -d "$P_U2" "$P_OLDGROUP"
groupdel "legacy-$P_RENAMED"; groupadd "$P_RENAMED"
