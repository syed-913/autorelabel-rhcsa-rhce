## A VFAT file system

```bash
dnf install -y dosfstools              # provides mkfs.vfat / mkfs.fat
parted {{lab.node1.disk1}} mkpart fat <start>MiB <start+300>MiB; partprobe
mkfs.vfat {{lab.node1.disk1}}N
blkid {{lab.node1.disk1}}N             # VFAT UUIDs look like 1A2B-3C4D
mkdir /mnt/{{dir}}
echo 'UUID=1A2B-3C4D /mnt/{{dir}} vfat defaults 0 0' >> /etc/fstab
systemctl daemon-reload; mount -a; findmnt /mnt/{{dir}}
```

References: RHEL 10 *Managing file systems*; `man mkfs.fat`.
