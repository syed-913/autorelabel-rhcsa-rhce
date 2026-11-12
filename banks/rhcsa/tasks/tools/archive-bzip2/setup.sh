#!/usr/bin/env bash
# The directory's files as the exam starts, for the check: later tasks may add files to it.
mkdir -p /etc/autorelabel
(cd / && find "${P_DIR#/}" ! -type d | LC_ALL=C sort) > "/etc/autorelabel/$P_NAME-backup.files"
