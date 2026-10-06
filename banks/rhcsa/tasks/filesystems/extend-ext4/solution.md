## Extend ext4 when the VG is full

```bash
vgs {{vg}}                                      # VFree 0
parted {{lab.node2.disk1}} mkpart lvm <s>MiB <s+600>MiB; partprobe
pvcreate {{lab.node2.disk1}}N
vgextend {{vg}} {{lab.node2.disk1}}N
lvextend -r -L 720M {{vg}}/homelv               # -r runs resize2fs for ext4
df -h /srv/{{vg}}-home
```

Without `-r`: `resize2fs /dev/{{vg}}/homelv` after `lvextend`.

References: RHEL 10 *Configuring and managing logical volumes*; `man resize2fs`.
