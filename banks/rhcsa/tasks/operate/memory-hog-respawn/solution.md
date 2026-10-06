## A respawning memory hog

```bash
ps -eo pid,comm,rss --sort=-rss | head        # or top, then press M
ps -o comm= -p <PID> > /root/memory-hog.txt
kill <PID>; sleep 70; pgrep -a {{word}}-cache     # it is back: something restarts it
systemctl status <PID>                         # not a service unit...
grep -r {{word}}-cache /etc/cron* /var/spool/cron # ...a cron job
rm /etc/cron.d/{{word}}-cache; pkill {{word}}-cache
```

**Classic mistake:** only killing the process. The cron entry starts it again every minute.

References: RHEL 10 *Monitoring and managing system status and performance*; `man ps`, `man 5 crontab`.
