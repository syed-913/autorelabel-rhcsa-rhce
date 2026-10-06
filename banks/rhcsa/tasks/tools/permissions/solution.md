## Ownership and permissions

```bash
chown {{user}}:{{group}} /srv/{{word}}/report.txt /srv/{{word}}/run.sh
chmod 640 /srv/{{word}}/report.txt              # rw-r-----
chmod u=rwx,g=rx,o= /srv/{{word}}/run.sh        # rwxr-x--- (= 750)
chown root:{{group}} /srv/{{word}}
chmod 750 /srv/{{word}}                         # group: list (r) and enter (x), no create (w)
ls -l /srv/{{word}}; ls -ld /srv/{{word}}
```

References: `man chmod` (symbolic and octal modes), `man chown`.
