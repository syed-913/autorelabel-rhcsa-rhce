#!/usr/bin/env bash
usermod -c "$P_COMMENT" -s /bin/sh -aG "$P_NEWGROUP" "$P_KEEP"
userdel -r "$P_GONE"
groupdel "$P_OLDGROUP"
