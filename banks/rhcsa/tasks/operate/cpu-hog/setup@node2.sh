#!/usr/bin/env bash
cat > "/usr/local/bin/${P_WORD}d" <<'SH'
#!/bin/bash
# busy loop (lab exercise)
while :; do :; done
SH
chmod 0755 "/usr/local/bin/${P_WORD}d"
restorecon "/usr/local/bin/${P_WORD}d"
# Installed where a package would put it, so it can be disabled or masked.
cat > "/usr/lib/systemd/system/$P_WORD-worker.service" <<UNIT
[Unit]
Description=$P_WORD background worker

[Service]
ExecStart=/usr/local/bin/${P_WORD}d
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now "$P_WORD-worker.service"
