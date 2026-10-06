## autofs direct map

```bash
dnf install -y autofs nfs-utils
echo '/- /etc/auto.direct' > /etc/auto.master.d/direct.autofs
echo '{{dir}} -ro {{lab.nfs_server}}:/exports/direct' > /etc/auto.direct
systemctl enable --now autofs
ls {{dir}}
```

`/-` in the master map means "direct map": keys are absolute paths.

References: RHEL 10 *Configuring and using network file services* → autofs; `man auto.master`.
