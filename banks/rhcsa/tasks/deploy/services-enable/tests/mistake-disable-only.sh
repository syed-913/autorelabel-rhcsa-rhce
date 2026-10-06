#!/usr/bin/env bash
# Common mistake: disable stops it at boot, but it can still be started manually or pulled in.
systemctl enable --now rsyslog
systemctl disable --now "$P_WORD-agent.service"
