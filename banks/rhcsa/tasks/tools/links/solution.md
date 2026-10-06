## Hard and symbolic links

```bash
ln    /data/{{word}}/2026.dat /srv/{{word}}/current.dat            # hard: TARGET then LINK NAME
ln -s /opt/{{word}}/bin/{{word}}-cli /usr/local/bin/{{word}}       # symbolic
ls -li /data/{{word}}/2026.dat /srv/{{word}}/current.dat           # same inode number
ls -l /usr/local/bin/{{word}}
```

A hard link is another name for the same inode (same file system only); a symbolic link is a
small file containing a path.

References: `man ln`.
