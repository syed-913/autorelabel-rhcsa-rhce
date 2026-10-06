#!/usr/bin/env bash
grubby --update-kernel=ALL --args="systemd.unit=emergency.target"
