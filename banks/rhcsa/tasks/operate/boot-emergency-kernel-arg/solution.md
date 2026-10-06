## Always booting into emergency mode

```bash
cat /proc/cmdline                         # ... systemd.unit=emergency.target
grubby --update-kernel=ALL --remove-args="systemd.unit=emergency.target"
reboot
```

A `systemd.unit=` kernel argument overrides `systemctl get-default`. (That is also how you boot
into a target **manually**: at the GRUB menu press `e` and append `systemd.unit=rescue.target`.)

References: RHEL 10 *Managing, monitoring, and updating the kernel*; `man kernel-command-line`.
