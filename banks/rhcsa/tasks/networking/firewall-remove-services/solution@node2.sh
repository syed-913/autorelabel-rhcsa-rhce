#!/usr/bin/env bash
firewall-cmd --permanent --remove-service=cockpit --remove-service=dhcpv6-client --remove-port="$P_PORT/tcp"
firewall-cmd --reload
