#!/usr/bin/env bash
# Records a scene against the Exam Desk of the current exam in <workspace>, on a real lab.
#   record-desk.sh <workspace> <scene.mjs> <output prefix>
# The desk is started for the take and stopped after it; the exam and its lab are left as they are.
set -euo pipefail
here=$(cd "$(dirname "$0")/../../.." && pwd)
py=${PYTHON:-python3}
log=$(mktemp)
export AUTORELABEL_WORKSPACE=$1 AUTORELABEL_ROOT=$here PYTHONPATH=$here/src
"$py" -u -m autorelabel desk --no-browser >"$log" 2>&1 &
desk=$!
trap 'kill $desk 2>/dev/null; rm -f "$log"' EXIT
for _ in $(seq 1 60); do grep -q '^Code:' "$log" && break; sleep 0.25; done
url=$(grep -o 'http://127.0.0.1:[0-9]*/' "$log" | head -1)
DESK_CODE=$(awk '/^Code:/ {print $2}' "$log")
DESK_NODE1_PASSWORD=$("$py" -c 'from autorelabel import session as S; print(S.current().given.get("node1", ""))')
export DESK_CODE DESK_NODE1_PASSWORD
node "$here/scripts/dev/demo/record.mjs" "$2" "$3" "$url"
