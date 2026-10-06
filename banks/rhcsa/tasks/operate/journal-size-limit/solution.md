## Persistent journal with a size limit

```bash
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/persistent.conf <<'X'
[Journal]
Storage=persistent
SystemMaxUse={{size}}M
X
systemctl restart systemd-journald
journalctl --disk-usage
```

`SystemMaxUse` limits the persistent journal in `/var/log/journal`; `RuntimeMaxUse` the volatile
one in `/run`.

References: `man journald.conf`.
