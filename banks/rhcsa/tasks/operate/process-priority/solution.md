## Process priority

Running process (temporary): `renice -n {{nice}} -p <PID>`.
Persistently for a service, add a drop-in:

```bash
systemctl edit {{word}}-indexer.service
```

```ini
[Service]
Nice={{nice}}
```

```bash
systemctl restart {{word}}-indexer.service
ps -o pid,ni,comm -p $(systemctl show -p MainPID --value {{word}}-indexer.service)
```

`systemctl edit` creates `/etc/systemd/system/{{word}}-indexer.service.d/override.conf`, which
survives package updates (never edit files in `/usr/lib/systemd/system/`). Starting a new
command with a priority: `nice -n {{nice}} <command>`.

**Classic mistake:** only `renice`. It is gone after the next restart or reboot.

References: RHEL 10 *Monitoring and managing system status and performance* (process priority);
`man systemd.exec` (`Nice=`).
