## Extend an LV and its XFS file system

```bash
vgs {{vg}}                                   # enough free space?
lvextend -r -L {{target}}M {{vg}}/datalv     # -r also grows the file system
df -h /srv/{{vg}}
```

Without `-r`: `lvextend ...` then `xfs_growfs /srv/{{vg}}`. (XFS can only grow, never shrink.)

References: RHEL 10 *Configuring and managing logical volumes*; `man lvextend`, `man xfs_growfs`.
