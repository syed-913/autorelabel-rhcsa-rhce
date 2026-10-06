## Repair an emergency-mode boot

On the console, log in with the root password at the maintenance prompt:

```bash
journalctl -xb | grep -iE 'timed out|dependency failed'   # which mount failed?
cat /etc/fstab
lsblk -f {{lab.node1.disk1}}                    # the real UUID of the ext4 file system
mount -o remount,rw /                           # if / is read-only
vim /etc/fstab                                  # correct the UUID for /{{mnt}}
systemctl daemon-reload
mount -a                                        # must succeed silently
systemctl default                               # or: reboot
```

To boot into a target manually: at the GRUB menu press `e` and append `systemd.unit=rescue.target`
(or `emergency.target`) to the `linux` line; from a running system, `systemctl isolate rescue.target`.

**Classic mistakes:** deleting the fstab line or adding `nofail`. The system boots, but the file
system the task requires is not mounted.

References: RHEL 10 *Managing, monitoring, and updating the kernel* → rescue/emergency mode;
`man systemd.special`, `man fstab`.
