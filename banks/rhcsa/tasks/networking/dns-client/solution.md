## DNS client and hostname

```bash
nmcli connection modify <conn> ipv4.dns {{lab.dns}} ipv4.dns-search lab.example.com
nmcli connection up <conn>
cat /etc/resolv.conf                 # written by NetworkManager
hostnamectl set-hostname {{short}}.lab.example.com
getent hosts utility
```

**Classic mistake:** editing `/etc/resolv.conf` directly. NetworkManager owns the file and
regenerates it from the connection settings at the next boot.

References: RHEL 10 *Configuring and managing networking* → DNS; `man nmcli`.
