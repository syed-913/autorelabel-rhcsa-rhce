## Create users and a group

```bash
groupadd -g {{gid}} {{group}}
useradd -G {{group}} {{user1}}
useradd -G {{group}} {{user2}}
useradd -u {{uid3}} -s /sbin/nologin {{user3}}
for u in {{user1}} {{user2}} {{user3}}; do echo "{{password}}" | passwd --stdin $u; done
id {{user1}}; getent group {{group}}
```

`-G` sets **supplementary** groups; `-g` sets the **primary** group. `/sbin/nologin` (or
`/bin/false`) prevents interactive logins.

References: RHEL 10 *Managing users and groups*; `man useradd`.
