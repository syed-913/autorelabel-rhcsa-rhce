## Install a package group

```bash
dnf group list                    # find the exact name
dnf group info "System Tools"     # what it contains
dnf group install -y "System Tools"
dnf group list --installed
```

References: RHEL 10 *Managing software with the DNF tool* → package groups.
