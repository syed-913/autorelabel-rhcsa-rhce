## A systemd timer

`/etc/systemd/system/{{word}}-report.service`:

```ini
[Unit]
Description={{word}} daily report

[Service]
Type=oneshot
ExecStart=/usr/bin/logger -t {{word}} "timer job"
```

`/etc/systemd/system/{{word}}-report.timer`:

```ini
[Timer]
OnCalendar=*-*-* {{hour}}:{{minute}}:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload
systemctl enable --now {{word}}-report.timer
systemctl list-timers {{word}}*
systemd-analyze calendar '*-*-* {{hour}}:{{minute}}:00'   # check your calendar expression
```

**Classic mistake:** enabling the `.service` instead of the `.timer`. Only the timer needs an
`[Install]` section and `enable`.

References: RHEL 10 *Using systemd unit files* → timers; `man systemd.timer`, `man systemd.time`.
