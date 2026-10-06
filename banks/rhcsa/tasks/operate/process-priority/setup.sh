#!/usr/bin/env bash
cat > "/usr/lib/systemd/system/$P_WORD-indexer.service" <<UNIT
[Unit]
Description=$P_WORD background indexer

[Service]
ExecStart=/usr/bin/sleep infinity

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now "$P_WORD-indexer.service"
