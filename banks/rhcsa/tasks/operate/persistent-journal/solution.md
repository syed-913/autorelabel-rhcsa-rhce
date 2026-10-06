## Persistent journal

RHEL 10 keeps the journal in `/run/log/journal` (lost at reboot) unless `/var/log/journal`
exists or `Storage=persistent` is set.

```bash
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=persistent\n' > /etc/systemd/journald.conf.d/persistent.conf
systemctl restart systemd-journald
journalctl --list-boots          # after a reboot: more than one boot listed
```

Just `mkdir /var/log/journal` (with the default `Storage=auto`) also works.

References: RHEL 10 documentation on systemd-journald persistent storage; `man journald.conf`.
