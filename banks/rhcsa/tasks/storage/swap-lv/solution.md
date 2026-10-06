## Swap on a logical volume

```bash
vgs {{vg}}                                     # enough free space?
lvcreate -L {{size}}M -n swaplv {{vg}}
mkswap /dev/{{vg}}/swaplv
echo '/dev/{{vg}}/swaplv none swap defaults 0 0' >> /etc/fstab
swapon -a; swapon --show
```

References: RHEL 10 *Managing storage devices* → swap on LVM; `man lvcreate`.
