#!/usr/bin/env bash
# Valid alternative: "HH:MM" calendar shorthand (normalizes to *-*-* HH:MM:00).
mkdir -p /etc/systemd/system
printf '[Service]\nType=oneshot\nExecStart=/usr/bin/logger -t %s "timer job"\n' "$P_WORD" \
  > "/etc/systemd/system/$P_WORD-report.service"
printf '[Timer]\nOnCalendar=%s:%s\n[Install]\nWantedBy=timers.target\n' "$P_HOUR" "$P_MINUTE" \
  > "/etc/systemd/system/$P_WORD-report.timer"
systemctl daemon-reload
systemctl enable --now "$P_WORD-report.timer"
