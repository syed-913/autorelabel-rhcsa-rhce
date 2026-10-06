## Grow a volume group

```bash
parted {{lab.node2.disk1}} mkpart lvm <start>MiB <start+500>MiB    # or fdisk: n, +500M, t → lvm
partprobe
pvcreate {{lab.node2.disk1}}N
vgextend {{vg}} {{lab.node2.disk1}}N
vgs {{vg}}
```

`vgextend` would also initialize the PV implicitly, but running `pvcreate` first is clearer.

References: RHEL 10 *Configuring and managing logical volumes*; `man vgextend`.
