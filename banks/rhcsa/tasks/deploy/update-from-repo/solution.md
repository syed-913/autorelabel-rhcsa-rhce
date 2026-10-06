## Update from an additional repository

`/etc/yum.repos.d/extras.repo`:

```ini
[extras]
name=Lab extras
baseurl=http://{{lab.utility_fqdn}}/extras/
enabled=1
gpgcheck=0
```

```bash
dnf repolist
dnf upgrade -y labtools        # or: dnf update labtools
rpm -q labtools                # labtools-1.1-...
```

**Classic mistakes:** `--nogpgcheck` on the command line (the repository definition still says
gpgcheck=1, so the next update fails again); `gpgcheck=0` in `/etc/dnf/dnf.conf` (turns signature
checking off for every repository).

References: RHEL 10 *Managing software with the DNF tool* → custom repositories; `man dnf.conf`.
