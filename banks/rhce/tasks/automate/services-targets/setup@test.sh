#!/usr/bin/env bash
# Start from a different default target, so making multi-user.target the default is real work.
systemctl set-default graphical.target >/dev/null 2>&1
