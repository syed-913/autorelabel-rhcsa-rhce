## XFS and ext4

```bash
parted {{lab.node2.disk1}} mkpart a <s>MiB <s+400>MiB mkpart b <s+400>MiB <s+700>MiB; partprobe
mkfs.xfs  {{lab.node2.disk1}}N      # RHEL 10: XFS needs at least 300 MB
mkfs.ext4 {{lab.node2.disk1}}M
mkdir -p /srv/{{word}}-xfs /srv/{{word}}-ext4
# /etc/fstab (UUIDs from blkid)
UUID=<u1> /srv/{{word}}-xfs  xfs  defaults 0 0
UUID=<u2> /srv/{{word}}-ext4 ext4 defaults 0 2
systemctl daemon-reload; mount -a; findmnt -t xfs,ext4
```

References: RHEL 10 *Managing file systems*; *Considerations in adopting RHEL 10*.
