#!/usr/bin/env bash
p2="$(cat "/etc/autorelabel/$P_VG-pv2")"
vgreduce -q "$P_VG" "$p2"
pvremove -q "$p2"
