#!/usr/bin/env bash
cat > "/usr/local/bin/$P_NAME" <<'SCRIPT'
#!/bin/bash
p="$1"
if [ -L "$p" ]; then echo symlink
elif [ -d "$p" ]; then echo directory
elif [ -f "$p" ]; then echo file
elif [ -e "$p" ]; then echo other
else echo missing; exit 1
fi
exit 0
SCRIPT
chmod 0755 "/usr/local/bin/$P_NAME"
