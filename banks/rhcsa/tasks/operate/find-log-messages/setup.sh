#!/usr/bin/env bash
cat > "/usr/local/bin/$P_WORD-batch" <<SH
#!/bin/sh
logger -p user.info  -t $P_WORD "batch started"
logger -p user.err   -t $P_WORD "cannot open /data/$P_WORD/input.csv"
logger -p user.warning -t $P_WORD "retrying in 5 seconds"
logger -p user.crit  -t $P_WORD "batch aborted after 3 retries"
logger -p user.info  -t $P_WORD "batch finished"
SH
chmod 0755 "/usr/local/bin/$P_WORD-batch"
restorecon "/usr/local/bin/$P_WORD-batch"
cat > "/etc/systemd/system/$P_WORD-batch.service" <<UNIT
[Unit]
Description=$P_WORD nightly batch
After=rsyslog.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/$P_WORD-batch
StandardOutput=journal

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable "$P_WORD-batch.service"
systemctl enable --now rsyslog >/dev/null 2>&1 || true
