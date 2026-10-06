## Remove a logical volume cleanly

```bash
umount /scratch
vim /etc/fstab                 # delete the /scratch line
systemctl daemon-reload
lvremove {{vg}}/scratch
findmnt --verify               # checks fstab for problems before you reboot
```

**Classic mistake:** removing the LV but not its `/etc/fstab` line. At the next boot systemd
waits for the device and drops into **emergency mode**.

References: RHEL 10 *Configuring and managing logical volumes*; `man lvremove`.
