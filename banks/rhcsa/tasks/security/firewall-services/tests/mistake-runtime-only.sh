#!/usr/bin/env bash
firewall-cmd --add-service="$P_SERVICE"
firewall-cmd --add-port="$P_PORT/tcp"
