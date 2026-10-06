## Mount by label

```bash
parted {{lab.node1.disk1}} mkpart data <start>MiB <start+500>MiB; partprobe
mkfs.ext4 -L {{label}} {{lab.node1.disk1}}N        # (existing fs: e2label <dev> {{label}})
mkdir /mnt/{{label}}
echo 'LABEL={{label}} /mnt/{{label}} ext4 defaults 0 2' >> /etc/fstab
systemctl daemon-reload; mount -a; findmnt /mnt/{{label}}
```

References: RHEL 10 *Managing file systems*; `man mkfs.ext4`, `man fstab`.
