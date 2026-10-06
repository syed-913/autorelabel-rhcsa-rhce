## Compress and uncompress single files

```bash
cd /srv/{{word}}-logs
gzip app.log          # → app.log.gz (original removed)
bzip2 db.log          # → db.log.bz2
gunzip old.log.gz     # → old.log   (or: gzip -d)
ls
```

`-k` keeps the original file. The task asks for only the three resulting files.

References: `man gzip`, `man bzip2`.
