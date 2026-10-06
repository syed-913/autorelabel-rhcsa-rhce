## A low-priority scheduled job

```bash
crontab -e -u {{user}}
30 {{hour}} * * * nice -n {{nice}} /usr/bin/tar -czf /tmp/{{user}}-home.tgz /home/{{user}}
```

`nice -n N command` starts a command with niceness N (19 = lowest priority). Regular users may
only make it nicer (higher), not lower.

References: `man nice`, `man 5 crontab`.
