#!/usr/bin/env bash
systemctl enable --now rsyslog
systemctl mask --now "$P_WORD-agent.service"
