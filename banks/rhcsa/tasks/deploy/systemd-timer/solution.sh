#!/usr/bin/env bash
cat > "/etc/systemd/system/$P_WORD-report.service" <<UNIT
[Unit]
Description=$P_WORD daily report

[Service]
Type=oneshot
ExecStart=/usr/bin/logger -t $P_WORD "timer job"
UNIT
cat > "/etc/systemd/system/$P_WORD-report.timer" <<UNIT
[Unit]
Description=Run $P_WORD-report daily

[Timer]
OnCalendar=*-*-* $P_HOUR:$P_MINUTE:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT
systemctl daemon-reload
systemctl enable --now "$P_WORD-report.timer"
