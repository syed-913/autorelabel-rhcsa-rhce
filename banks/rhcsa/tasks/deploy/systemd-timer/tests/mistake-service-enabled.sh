#!/usr/bin/env bash
# Common mistake: enabling the service instead of the timer (the timer never starts at boot).
printf '[Service]\nType=oneshot\nExecStart=/usr/bin/logger -t %s "timer job"\n[Install]\nWantedBy=multi-user.target\n' "$P_WORD" \
  > "/etc/systemd/system/$P_WORD-report.service"
printf '[Timer]\nOnCalendar=*-*-* %s:%s:00\n' "$P_HOUR" "$P_MINUTE" > "/etc/systemd/system/$P_WORD-report.timer"
systemctl daemon-reload
systemctl enable "$P_WORD-report.service"
systemctl start "$P_WORD-report.timer"
