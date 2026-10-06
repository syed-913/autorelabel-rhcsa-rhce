#!/usr/bin/env bash
firewall-cmd --permanent --add-service="$P_SERVICE"
firewall-cmd --permanent --add-port="$P_PORT/tcp"
firewall-cmd --reload
