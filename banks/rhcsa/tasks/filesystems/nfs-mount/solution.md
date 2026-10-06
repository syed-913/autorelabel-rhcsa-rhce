## Persistent NFS mount

```bash
dnf install -y nfs-utils
showmount -e {{lab.nfs_server}}          # (NFSv3 helper; may be blocked; NFSv4 still works)
mkdir -p /mnt/{{share}}
echo '{{lab.nfs_server}}:/exports/{{share}} /mnt/{{share}} nfs defaults,_netdev 0 0' >> /etc/fstab
systemctl daemon-reload; mount -a; findmnt /mnt/{{share}}
```

`_netdev` marks it as a network mount (systemd recognizes `nfs` automatically, but it does
no harm and documents intent).

**Classic mistake:** `mount -t nfs ...` only. It is gone after the reboot.

References: RHEL 10 *Configuring and using network file services* → mounting NFS shares; `man nfs`.
