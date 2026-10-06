## A collaborative directory

```bash
mkdir -p /common/{{group}}
chown root:{{group}} /common/{{group}}
chmod 3770 /common/{{group}}      # 2000 setgid + 1000 sticky + 770
ls -ld /common/{{group}}          # drwxrws--T
```

- **setgid** on a directory: new files get the directory's group.
- **sticky bit**: only a file's owner (or root) may delete or rename it.

References: RHEL 10 *Managing file systems* → special permissions; `man chmod`.
