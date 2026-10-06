## Broken links

```bash
find /opt/{{word}}/current -xtype l               # dangling symbolic links
ln -sfn /opt/{{word}}/releases/2.0/app.bin /opt/{{word}}/current/app.bin   # -f replace, -n don't follow
ln /opt/{{word}}/releases/2.0/settings.conf /opt/{{word}}/backup/settings.conf
ls -li /opt/{{word}}/backup /opt/{{word}}/releases/2.0
```

References: `man find` (`-xtype`), `man ln`.
