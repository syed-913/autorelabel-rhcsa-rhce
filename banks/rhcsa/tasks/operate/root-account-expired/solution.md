## Locked and expired root

Same `rd.break` procedure as a password reset, plus one more fix in the chroot:

```bash
# GRUB: e → append rd.break → Ctrl+x
mount -o remount,rw /sysroot
chroot /sysroot
passwd root                  # {{new_password}}
chage -l root                # "Account expires: Jan 01, 1970"
chage -E -1 root             # never expires
touch /.autorelabel
exit; exit
```

References: RHEL *Resetting the forgotten root password on boot*; `man chage`.
