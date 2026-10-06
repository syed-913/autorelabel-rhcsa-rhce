## Find files and copy them

```bash
mkdir -p /root/{{user}}-files
find / -user {{user}} -type f -exec cp -p {} /root/{{user}}-files/ \; 2>/dev/null
ls -la /root/{{user}}-files
```

`-type f` restricts to regular files; `cp -p` (or `cp -a`) preserves owner, mode and timestamps;
`2>/dev/null` hides "Permission denied"/`/proc` noise. (`find` also searches `/home`, so the user's
own dotfiles are included: they are files owned by `{{user}}`.)

**Classic mistakes:** plain `cp` (the copies are owned by root with new times); omitting `-type f`
(directories are copied too).

References: `man find`, `man cp`.
