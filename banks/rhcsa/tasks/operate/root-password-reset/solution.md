## Recover root access on node2 (rd.break)

1. Open the console: `./autorelabel console node2`, then reboot the node
   (`./autorelabel node reset node2` from another terminal works when you cannot log in).
2. At the GRUB menu, highlight the default entry and press **`e`**.
3. Go to the line starting with `linux` and append **`rd.break`** at its end.
   Press **Ctrl+x** to boot.
4. In the `switch_root:/#` shell:

```bash
mount -o remount,rw /sysroot
chroot /sysroot
passwd root                 # type {{new_password}} twice
touch /.autorelabel         # SELinux: relabel on next boot (essential)
exit
exit                        # boot continues; the relabel runs, then the node reboots once more
```

The relabel can take a minute or two; the node reboots by itself when it finishes. Log in as root
with `{{new_password}}` to confirm.

**Classic mistake:** forgetting `touch /.autorelabel`. `passwd` creates a new `/etc/shadow`
without a valid SELinux label, so after the reboot nobody, root included, can log in.
(Alternative inside the chroot: `load_policy -i` before `passwd`, then `restorecon -v /etc/shadow`
after it.)

References: RHEL *Configuring basic system settings* → "Resetting the forgotten root password on
boot"; `man dracut.cmdline` (`rd.break`).
