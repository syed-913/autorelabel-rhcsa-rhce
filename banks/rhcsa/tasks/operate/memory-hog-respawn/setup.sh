#!/usr/bin/env bash
cat > "/usr/local/bin/$P_WORD-cache" <<'PY'
#!/usr/bin/python3
# lab exercise: holds ~150 MB of memory
import time
blob = bytearray(150 * 1024 * 1024)
for i in range(0, len(blob), 4096):
    blob[i] = 1
while True:
    time.sleep(60)
PY
chmod 0755 "/usr/local/bin/$P_WORD-cache"; restorecon "/usr/local/bin/$P_WORD-cache"
cat > "/etc/cron.d/$P_WORD-cache" <<CRON
* * * * * root pgrep -x $P_WORD-cache >/dev/null || /usr/local/bin/$P_WORD-cache >/dev/null 2>&1 &
CRON
chmod 0644 "/etc/cron.d/$P_WORD-cache"
nohup "/usr/local/bin/$P_WORD-cache" >/dev/null 2>&1 &
