## Using the documentation

```bash
dnf install -y info
info coreutils 'date invocation'      # → "Date conversion specifiers": %V = ISO week number
printf '#!/bin/bash\ndate +%%V\n' > /usr/local/bin/isoweek; chmod 755 /usr/local/bin/isoweek
rpm -qd rsync | grep NEWS > /root/rsync-news.txt     # or: ls /usr/share/doc/rsync/
```

`%U` and `%W` are week numbers too, but not ISO 8601 ones, and they differ around year
boundaries. `rpm -qd <package>` lists a package's documentation files.

References: `info coreutils`, `man date`, `man rpm` (`-qd`).
