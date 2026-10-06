#!/usr/bin/env bash
# Common mistake: usage message on stdout and exit 1.
cat > "/usr/local/bin/$P_NAME" <<'SCRIPT'
#!/bin/bash
if [ -z "$1" ]; then echo "Usage: $(basename "$0") USERNAME"; exit 1; fi
if id "$1" >/dev/null 2>&1; then echo "$1 exists with UID $(id -u "$1")"; else echo "$1 not found"; exit 1; fi
SCRIPT
chmod 0755 "/usr/local/bin/$P_NAME"
