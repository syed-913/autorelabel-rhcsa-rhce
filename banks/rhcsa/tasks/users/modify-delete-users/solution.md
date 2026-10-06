## Modify and remove accounts

```bash
usermod -c "{{comment}}" -s /bin/sh -aG {{newgroup}} {{keep}}
userdel -r {{gone}}          # -r: also remove the home directory and mail spool
groupdel {{oldgroup}}
id {{keep}}; getent passwd {{keep}}
```

**Classic mistakes:** `usermod -G` without `-a` replaces all supplementary groups (here
`{{keep}}` would lose `wheel`); `userdel` without `-r` leaves `/home/{{gone}}` behind.

References: RHEL 10 *Managing users and groups*; `man usermod`, `man userdel`.
