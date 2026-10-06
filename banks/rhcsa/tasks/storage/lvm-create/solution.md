## LVM with a specific extent size

```bash
parted {{lab.node1.disk1}} mkpart lvm <start>MiB <start+1024>MiB      # or fdisk: n, +1G, t → lvm
partprobe; lsblk {{lab.node1.disk1}}
pvcreate {{lab.node1.disk1}}N
vgcreate -s {{pe}}M {{vg}} {{lab.node1.disk1}}N
lvcreate -l {{extents}} -n {{lv}} {{vg}}               # -l = extents, -L = size
mkfs.xfs /dev/{{vg}}/{{lv}}
mkdir -p /mnt/{{lv}}
blkid /dev/{{vg}}/{{lv}}                                # copy the UUID
echo 'UUID=<uuid> /mnt/{{lv}} xfs defaults 0 0' >> /etc/fstab
systemctl daemon-reload; mount -a; findmnt /mnt/{{lv}}
```

Always test fstab with `mount -a` (and `findmnt --verify`) **before** rebooting. A bad line can
drop the system into emergency mode.

References: RHEL 10 *Configuring and managing logical volumes*; *Managing file systems*;
`man vgcreate` (`-s`), `man lvcreate` (`-l`).
