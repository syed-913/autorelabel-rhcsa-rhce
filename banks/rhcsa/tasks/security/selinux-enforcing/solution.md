## SELinux enforcing mode

Two places matter:

```bash
setenforce 1                                        # now (runtime)
sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config   # at every boot
getenforce; sestatus
```

**Classic mistake:** only running `setenforce 1`. It is lost at reboot, and the system comes back
permissive.

References: RHEL 10 *Using SELinux* → "Changing to enforcing mode"; `man selinux_config`.
