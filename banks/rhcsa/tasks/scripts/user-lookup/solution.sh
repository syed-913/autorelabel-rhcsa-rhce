#!/usr/bin/env bash
cat > "/usr/local/bin/$P_NAME" <<'SCRIPT'
#!/bin/bash
if [ $# -ne 1 ]; then
    echo "Usage: $(basename "$0") USERNAME" >&2
    exit 2
fi
if id "$1" >/dev/null 2>&1; then
    echo "$1 exists with UID $(id -u "$1")"
    exit 0
else
    echo "$1 not found"
    exit 1
fi
SCRIPT
chmod 0755 "/usr/local/bin/$P_NAME"
