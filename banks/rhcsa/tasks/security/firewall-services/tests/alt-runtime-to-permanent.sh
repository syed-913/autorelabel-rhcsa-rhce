#!/usr/bin/env bash
# Valid alternative: change the runtime, then save it.
firewall-cmd --add-service="$P_SERVICE"
firewall-cmd --add-port="$P_PORT/tcp"
firewall-cmd --runtime-to-permanent
