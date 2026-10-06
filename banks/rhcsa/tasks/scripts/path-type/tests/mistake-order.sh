#!/usr/bin/env bash
# Common mistake: testing -d/-f before -L (a link to a directory is reported as "directory").
cat > "/usr/local/bin/$P_NAME" <<'SCRIPT'
#!/bin/bash
if [ -d "$1" ]; then echo directory
elif [ -f "$1" ]; then echo file
elif [ -L "$1" ]; then echo symlink
elif [ -e "$1" ]; then echo other
else echo missing; exit 1; fi
SCRIPT
chmod 0755 "/usr/local/bin/$P_NAME"
