#!/usr/bin/env bash
# Messages go to stdout with sd-daemon priority prefixes (<3> = err): systemd hands the stream
# to the journal for this unit, so every line is attributed to it. (Short-lived `logger`
# processes race journald's unit lookup, and a varying subset would show up under -u.)
cat > "/usr/local/bin/$P_WORD-batch" <<SH
#!/bin/sh
echo "<6>batch started"
echo "<3>cannot open /data/$P_WORD/input.csv"
echo "<4>retrying in 5 seconds"
echo "<2>batch aborted after 3 retries"
echo "<6>batch finished"
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
SyslogIdentifier=$P_WORD

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable "$P_WORD-batch.service"
systemctl enable --now rsyslog >/dev/null 2>&1 || true
