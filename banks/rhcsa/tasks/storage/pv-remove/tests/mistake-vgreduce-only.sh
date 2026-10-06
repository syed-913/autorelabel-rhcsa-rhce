#!/usr/bin/env bash
# Common mistake: vgreduce without pvremove (the PV label stays).
vgreduce -q "$P_VG" "$(cat "/etc/autorelabel/$P_VG-pv2")"
