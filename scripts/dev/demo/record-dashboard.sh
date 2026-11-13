#!/usr/bin/env bash
# Records a scene against a results dashboard serving <workspace>, started fresh for the take
# (its launch address works once).   record-dashboard.sh <workspace> <scene.mjs> <output prefix>
set -euo pipefail
here=$(cd "$(dirname "$0")/../../.." && pwd)
log=$(mktemp)
AUTORELABEL_WORKSPACE=$1 AUTORELABEL_ROOT=$here PYTHONPATH=$here/src "${PYTHON:-python3}" -u -m autorelabel dashboard \
  --no-browser >"$log" 2>&1 &
server=$!
trap 'kill $server 2>/dev/null; rm -f "$log"' EXIT
for _ in $(seq 1 40); do grep -q 'http://' "$log" && break; sleep 0.25; done
url=$(grep -o 'http://127.0.0.1:[0-9]*/open/[A-Za-z0-9_-]*' "$log")
node "$here/scripts/dev/demo/record.mjs" "$2" "$3" "$url"
