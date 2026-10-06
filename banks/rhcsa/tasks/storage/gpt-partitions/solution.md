## GPT partitions without data loss

```bash
lsblk {{lab.node2.disk1}}; parted {{lab.node2.disk1}} unit MiB print free
parted {{lab.node2.disk1}} rm <N>                       # N = the 256 MiB partition's number
parted {{lab.node2.disk1}} mkpart part1 <start>MiB <start+{{size1}}>MiB
parted {{lab.node2.disk1}} mkpart part2 <...>MiB <...>MiB
partprobe {{lab.node2.disk1}}; lsblk {{lab.node2.disk1}}
```

With `fdisk {{lab.node2.disk1}}`: `d` (delete), `n` (new, accept the default start, size `+{{size1}}M`),
`n` again (`+{{size2}}M`), `w`. `gdisk` works similarly.

**Classic mistake:** `mklabel` (a new partition table) or picking the wrong partition number.
The mounted data partition is destroyed. Always `lsblk`/`print` first.

References: RHEL 10 *Managing storage devices* → partitions; `man parted`, `man fdisk`.
