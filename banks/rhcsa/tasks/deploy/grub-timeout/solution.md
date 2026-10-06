## Boot loader menu timeout

```bash
vim /etc/default/grub                       # GRUB_TIMEOUT={{timeout}}
grub2-mkconfig -o /boot/grub2/grub.cfg      # regenerate (on UEFI too: this path is correct on RHEL 9/10)
grep timeout /boot/grub2/grub.cfg
```

**Classic mistake:** changing `/etc/default/grub` and not running `grub2-mkconfig`. GRUB reads
`grub.cfg`, not `/etc/default/grub`.

References: RHEL 10 *Managing, monitoring, and updating the kernel* → GRUB configuration.
