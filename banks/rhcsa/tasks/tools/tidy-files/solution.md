## Move, copy and delete

```bash
mkdir -p /srv/{{word}}-archive/2026/q3                 # -p creates parents
mv /srv/{{word}}-inbox/*.csv /srv/{{word}}-archive/2026/q3/
rm -f /srv/{{word}}-inbox/*.tmp
rmdir /srv/{{word}}-inbox/old                          # only removes empty directories
```

References: `man mv`, `man rm`, `man mkdir`.
