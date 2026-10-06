#!/usr/bin/env bash
# Common mistake: usermod -G without -a replaces all supplementary groups.
usermod -c "$P_COMMENT" -s /bin/sh -G "$P_NEWGROUP" "$P_KEEP"
userdel -r "$P_GONE"
groupdel "$P_OLDGROUP"
