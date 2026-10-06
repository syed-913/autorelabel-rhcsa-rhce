## Persistent SELinux booleans

```bash
getsebool -a | grep -E 'httpd|nfs|ftpd'     # find booleans
semanage boolean -l | grep httpd_enable     # with descriptions
setsebool -P <boolean> on                  # -P = persistent
```

`semanage boolean -m --on <boolean>` is equivalent. `semanage boolean -l -C` lists your
local customizations.

**Classic mistake:** `setsebool <boolean> on` without `-P`. It works until the next reboot.

References: RHEL 10 *Using SELinux* → "Adjusting the policy using booleans"; `man setsebool`.
