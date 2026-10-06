#!/usr/bin/env bash
cat > "/usr/local/bin/$P_NAME" <<'SCRIPT'
#!/bin/bash
for arg in "$@"; do
    echo "$arg: ${#arg}"
done
echo "total: $#"
SCRIPT
chmod 0755 "/usr/local/bin/$P_NAME"
