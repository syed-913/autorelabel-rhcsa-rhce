## Time service client (chrony)

```bash
vim /etc/chrony.conf              # comment out the default 'pool' line, add:
server {{lab.ntp_server}} iburst
systemctl enable --now chronyd    # restart it if it was already running
chronyc sources -v                # ^* means synchronized; ^? means not yet
timedatectl                       # "NTP service: active"
```

**Classic mistake:** the service was disabled. Configuring the file and running
`systemctl start` is not enough; it must also be **enabled**.

References: RHEL 10 *Configuring time synchronization*; `man chrony.conf`, `man chronyc`.
