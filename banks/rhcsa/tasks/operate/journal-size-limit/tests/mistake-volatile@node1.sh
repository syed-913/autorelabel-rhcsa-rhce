#!/usr/bin/env bash
# Common mistake: the size limit for the wrong storage (Runtime*) and no persistence.
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nRuntimeMaxUse=%sM\n' "$P_SIZE" > /etc/systemd/journald.conf.d/lab.conf
systemctl restart systemd-journald
