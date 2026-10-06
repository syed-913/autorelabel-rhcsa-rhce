#!/usr/bin/env bash
cat > "/usr/local/bin/$P_NAME" <<'SCRIPT'
#!/bin/bash
while read -r host; do
    [[ -z "$host" || "$host" == \#* ]] && continue
    addr="$(getent ahostsv4 "$host" | awk 'NR==1 {print $1}')"
    echo "$host ${addr:-unknown}"
done < "$1"
SCRIPT
chmod 0755 "/usr/local/bin/$P_NAME"
