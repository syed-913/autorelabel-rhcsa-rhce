## Time zone and NTP

```bash
timedatectl list-timezones | grep -i {{tz}}
timedatectl set-timezone {{tz}}
vim /etc/chrony.conf       # comment out "pool 2.rhel.pool.ntp.org iburst", add:
server {{lab.ntp_server}} iburst
systemctl restart chronyd; timedatectl set-ntp true
chronyc sources; timedatectl
```

References: RHEL 10 *Configuring time synchronization*; `man timedatectl`.
