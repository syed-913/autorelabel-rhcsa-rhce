## A user's cron job

```bash
crontab -e -u {{user}}
```

```
# minute hour day-of-month month day-of-week command
{{minute}} {{hour}} * * {{dow}} logger -t {{word}} "scheduled job ran"
```

`crontab -l -u {{user}}` to verify. The field order is **minute, hour, day of month, month, day of
week**.

References: RHEL 10 *Scheduling recurring jobs with cron*; `man 5 crontab` (field layout and
examples).
