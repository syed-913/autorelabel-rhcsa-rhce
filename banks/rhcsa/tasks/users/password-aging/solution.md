## Password aging

Existing accounts: `chage`. Future accounts: `/etc/login.defs`.

```bash
chage -M {{maxdays}} -W {{warn}} -E {{expire}} {{user}}
chage -d 0 {{user}}                  # or: passwd -e {{user}}
chage -l {{user}}
sed -i 's/^PASS_MAX_DAYS.*/PASS_MAX_DAYS   {{defmax}}/' /etc/login.defs
```

**Classic mistake:** editing `/etc/login.defs` and expecting existing users to change. It is only
read when an account is created.

References: RHEL 10 *Managing users and groups*; `man chage`, `man login.defs`.
