#!/usr/bin/env bash
firewall-cmd --remove-service=cockpit --remove-service=dhcpv6-client
firewall-cmd --remove-port="$P_PORT/tcp"
