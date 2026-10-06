## A permanent kernel argument

```bash
grubby --update-kernel=ALL --args="{{arg}}"
grubby --info=ALL | grep args
reboot; cat /proc/cmdline
```

On RHEL 10 each kernel has a BLS entry in `/boot/loader/entries/`. `grubby --update-kernel=ALL`
updates them all (and the default for future kernels). If you prefer editing `/etc/default/grub`,
you must regenerate with `grub2-mkconfig -o /boot/grub2/grub.cfg --update-bls-cmdline`.

**Classic mistake:** editing `GRUB_CMDLINE_LINUX` in `/etc/default/grub` and nothing else.
Nothing changes at boot.

References: RHEL 10 *Managing, monitoring, and updating the kernel* → kernel command-line
parameters; `man grubby`.
