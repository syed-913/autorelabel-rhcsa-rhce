#!/usr/bin/env bash
cat > /usr/local/bin/sysreport <<'SCRIPT'
#!/bin/bash
echo "hostname=$(hostname)"
echo "kernel=$(uname -r)"
echo "selinux=$(getenforce)"
echo "users=$(wc -l < /etc/passwd)"
SCRIPT
chmod 0755 /usr/local/bin/sysreport
