#!/usr/bin/env bash
# The LV exactly at the lower bound, the file system grown with it: df shows 64 MiB less (the log).
lvextend -q -r -L "${P_TARGET}M" "$P_VG/datalv"
