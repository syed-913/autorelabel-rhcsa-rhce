## Find messages in the logs

```bash
journalctl -b -u {{word}}-batch.service -p err -o cat > /root/{{word}}-errors.txt
cat /root/{{word}}-errors.txt
grep -rl {{word}} /var/log/            # → /var/log/messages
```

`-p err` means **err and every more severe level** (crit, alert, emerg). `-p err..err` would be
exactly one level. `-b` is the current boot; `-o cat` prints only the message text.

References: RHEL 10 documentation on log files and journalctl; `man journalctl` (`-p`, `-u`, `-b`).
