## Extract and create archives

```bash
mkdir -p /srv/{{word}}-restore
tar -xvf /root/{{word}}-bundle.tar -C /srv/{{word}}-restore
tar -czvf /root/{{word}}-restore.tar.gz /srv/{{word}}-restore
tar -tzf /root/{{word}}-restore.tar.gz | head
```

`-C <dir>` extracts into that directory instead of the current one.

References: `man tar`.
