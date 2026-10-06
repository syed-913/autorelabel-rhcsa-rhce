#!/usr/bin/env bash
# Common mistake: userdel without -r leaves the home directory and mail spool behind.
usermod -c "$P_COMMENT" -s /bin/sh -aG "$P_NEWGROUP" "$P_KEEP"
userdel "$P_GONE"
groupdel "$P_OLDGROUP"
