#!/usr/bin/env bash
# Valid alternative: with Storage=auto, creating /var/log/journal is enough.
mkdir -p /var/log/journal
systemd-tmpfiles --create --prefix /var/log/journal
systemctl restart systemd-journald
