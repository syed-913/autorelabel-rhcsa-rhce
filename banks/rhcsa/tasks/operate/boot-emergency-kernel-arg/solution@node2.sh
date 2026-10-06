#!/usr/bin/env bash
grubby --update-kernel=ALL --remove-args="systemd.unit=emergency.target"
