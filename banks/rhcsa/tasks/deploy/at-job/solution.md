## A one-time job with at

```bash
dnf install -y at
systemctl enable --now atd
at 'HH:MM YYYY-MM-DD'          # e.g. the date in the task
at> /usr/bin/logger -t {{word}} "one-time job"
at> <Ctrl+D>
atq                             # list; at -c <id> shows the job
```

**Classic mistake:** `systemctl start atd` without `enable`. After a reboot the job is still in
the queue but nothing runs it.

References: RHEL 10 *Scheduling one-time jobs with at*; `man at`.
