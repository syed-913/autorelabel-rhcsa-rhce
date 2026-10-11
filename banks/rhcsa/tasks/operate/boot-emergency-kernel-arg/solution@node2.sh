#!/usr/bin/env bash
# Typed on the console in emergency mode: / is still read-only and /boot is not mounted.
mount -o remount,rw /
mount -a
grubby --update-kernel=ALL --remove-args="systemd.unit=emergency.target"
