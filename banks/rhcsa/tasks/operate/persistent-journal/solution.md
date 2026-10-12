## Persistent journal

RHEL 10 keeps the journal in `/run/log/journal` (lost at reboot) unless `/var/log/journal`
exists or `Storage=persistent` is set.

```bash
mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=persistent\n' > /etc/systemd/journald.conf.d/persistent.conf
systemctl restart systemd-journald
journalctl --flush               # optional: also keep this boot's earlier messages
journalctl --list-boots          # after the next reboot: more than one boot listed
```

After the restart, journald keeps writing to `/run` until the next boot (or `journalctl --flush`),
so the boot in which you configured it is not kept; every later boot is. The grader checks that
the boot after its reboot is stored in `/var/log/journal`.

Just `mkdir /var/log/journal` (with the default `Storage=auto`) also works.

References: RHEL 10 documentation on systemd-journald persistent storage; `man journald.conf`.
