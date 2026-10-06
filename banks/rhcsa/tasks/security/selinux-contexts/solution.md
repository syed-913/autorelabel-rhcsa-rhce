## Identify SELinux contexts

A context has four fields, `user:role:type:level`; the **type** is the third.

```bash
ps -eZ | grep {{process}}          # e.g. system_u:system_r:chronyd_t:s0 ... chronyd
ls -Z {{path}}                     # or: stat -c %C {{path}}
```

Then write just the two types into `/root/selinux-report.txt`, one per line.

References: RHEL 10 *Using SELinux*; `man ps` (`-Z`), `man ls` (`-Z`).
