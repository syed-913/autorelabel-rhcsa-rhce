## A one-time job with at

```bash
dnf install -y at
systemctl enable --now atd
at 'HH:MM YYYY-MM-DD'          # e.g. the date in the task
at> /usr/bin/logger -t {{word}} "one-time job"
at> <Ctrl+D>
atq                             # list; at -c <id> shows the job
```

**Classic mistake:** `at 09:30` without the date. That means the *next* 09:30 (today or
tomorrow), not the requested day. Always give both: `at '09:30 2027-01-15'`, then check `atq`.

On RHEL, installing `at` enables `atd` through the systemd preset, but verify it anyway with
`systemctl is-enabled atd`.

References: RHEL 10 *Scheduling one-time jobs with at*; `man at`.
