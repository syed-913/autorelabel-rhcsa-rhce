## Default permissions for one user

The umask removes bits from the defaults (666 for files, 777 for directories):
`rw-r-----` = 640 and `rwxr-x---` = 750 → umask **027**.

```bash
echo "umask 027" >> /home/{{user}}/.bashrc
su - {{user}} -c umask        # 0027
```

`~/.bash_profile` also works for login shells. Don't change `/etc/profile`, `/etc/bashrc` or
`/etc/login.defs`: those affect everyone.

**Classic mistake:** writing the permission you want (`umask 640`) instead of the bits to remove.

References: RHEL 10 *Managing file systems* → default umask; `man bash` (umask).
