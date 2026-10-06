## Swap on a new partition

```bash
parted {{lab.node2.disk1}} mkpart swap linux-swap <start>MiB <start+{{size}}>MiB    # or fdisk: n, +{{size}}M, t → swap
partprobe; lsblk {{lab.node2.disk1}}
mkswap {{lab.node2.disk1}}N
blkid {{lab.node2.disk1}}N
echo 'UUID=<uuid> none swap defaults 0 0' >> /etc/fstab
swapon -a; swapon --show; free -m
```

References: RHEL 10 *Managing storage devices* → swap; `man mkswap`, `man swapon`.
