## Mirror a directory with rsync

```bash
# on node1 (rsync installed on both)
rsync -av --delete /srv/{{word}}-site/ root@node2:/srv/{{word}}-site/
```

- `-a` keeps permissions, times, ownership, links
- `--delete` removes files on the target that no longer exist on the source
- the trailing `/` on the source means "the contents of" the directory

References: `man rsync`.
