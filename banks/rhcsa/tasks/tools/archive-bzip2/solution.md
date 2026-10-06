## A bzip2-compressed archive

```bash
tar -cjf /root/{{name}}-backup.tar.bz2 {{dir}}
tar -tjvf /root/{{name}}-backup.tar.bz2 | head
file /root/{{name}}-backup.tar.bz2
```

`-j` = bzip2, `-z` = gzip, `-J` = xz. (`tar` strips the leading `/`; that's expected.)

References: `man tar`.
