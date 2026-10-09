#!/usr/bin/env bash
# The node's state is fixed per host: node3 is critical, node2 has a warning, the rest are fine.
case "$AR_NODE" in
  node3) state="CRITICAL: service labd is not responding" ;;
  node2) state="WARNING: /var is 81% full" ;;
  *)     state="OK" ;;
esac
cat > /usr/local/bin/labcheck <<SH
#!/bin/sh
echo "STATUS: $state"
exit 0
SH
chmod 0755 /usr/local/bin/labcheck
