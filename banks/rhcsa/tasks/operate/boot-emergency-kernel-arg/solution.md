## Always booting into emergency mode

```bash
cat /proc/cmdline                         # ... systemd.unit=emergency.target
mount -o remount,rw /                     # emergency mode: / is read-only ...
mount -a                                  # ... and /boot is not mounted
grubby --update-kernel=ALL --remove-args="systemd.unit=emergency.target"
grubby --info=ALL | grep ^args            # check every entry
reboot
```

Without the two `mount` commands grubby fails with "Read-only file system" and
"/boot/grub2/grubenv: No such file or directory", and nothing changes.

A `systemd.unit=` kernel argument overrides `systemctl get-default`. (That is also how you boot
into a target **manually**: at the GRUB menu press `e` and append `systemd.unit=rescue.target`.)

References: RHEL 10 *Managing, monitoring, and updating the kernel*; `man kernel-command-line`.
