#!/usr/bin/env bash
firewall-cmd --remove-service=cockpit --remove-service=dhcpv6-client --remove-port="$P_PORT/tcp"
