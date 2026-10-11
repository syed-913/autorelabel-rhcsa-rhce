## DNS client and hostname

```bash
nmcli connection modify <conn> ipv4.dns {{lab.dns}} ipv4.dns-search lab.example.com
nmcli connection up <conn>
cat /etc/resolv.conf                 # written by NetworkManager
hostnamectl set-hostname {{short}}.lab.example.com
getent hosts utility
```

**Classic mistake:** editing `/etc/resolv.conf` directly. NetworkManager owns the file and
rewrites it from the connection settings whenever DNS information changes (a connection going up,
a DHCP lease), so the edit only survives until then. If you really want a hand-written
`/etc/resolv.conf`, first tell NetworkManager to leave it alone (`dns=none` in a file under
`/etc/NetworkManager/conf.d/`, then `systemctl reload NetworkManager`).

References: RHEL 10 *Configuring and managing networking* → DNS; `man nmcli`.
