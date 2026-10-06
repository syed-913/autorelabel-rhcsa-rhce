## A system cron job

Files in `/etc/cron.d/` use the **system** format, which has a sixth field: the user.

```
*/{{every}} * * * * root /usr/bin/logger -t {{word}} "system job"
```

Save it as e.g. `/etc/cron.d/{{word}}` (mode 644). crond picks it up automatically.

**Classic mistake:** using the user-crontab format (no user field). The line is then invalid.

References: RHEL 10 *Scheduling recurring jobs with cron*; `man 5 crontab`.
