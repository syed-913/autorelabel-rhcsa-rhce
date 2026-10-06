#!/usr/bin/env bash
firewall-cmd -q --permanent --add-port="$P_PORT/tcp"; firewall-cmd -q --reload
