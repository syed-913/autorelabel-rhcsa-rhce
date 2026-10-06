#!/usr/bin/env bash
systemctl disable --now rsyslog
cat > "/usr/lib/systemd/system/$P_WORD-agent.service" <<UNIT
[Unit]
Description=$P_WORD monitoring agent (lab)

[Service]
ExecStart=/usr/bin/sleep infinity

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now "$P_WORD-agent.service"
