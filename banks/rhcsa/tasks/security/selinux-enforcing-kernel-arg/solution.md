## Why SELinux stays permissive

A kernel argument overrides `/etc/selinux/config`. Look at the running kernel's command line and
every boot entry:

```bash
cat /proc/cmdline                       # ... enforcing=0
grubby --info=ALL | grep -E 'args|kernel'
grubby --update-kernel=ALL --remove-args="enforcing=0"
setenforce 1
```

`--update-kernel=ALL` also fixes the rescue entry and future kernels. On RHEL 10, kernel
arguments live in the BLS entries (`/boot/loader/entries/*.conf`); `grubby` edits them for you.

**Classic mistakes:** only `setenforce 1` (lost at reboot); editing `/etc/default/grub` without
regenerating anything; fixing only the default kernel.

References: RHEL 10 *Using SELinux* (kernel parameters `enforcing=`/`selinux=`);
*Managing, monitoring, and updating the kernel* → grubby; `man grubby`.
