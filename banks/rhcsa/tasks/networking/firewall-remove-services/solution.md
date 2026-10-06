## Remove firewall openings

```bash
firewall-cmd --list-all
firewall-cmd --permanent --remove-service=cockpit --remove-service=dhcpv6-client --remove-port={{port}}/tcp
firewall-cmd --reload
firewall-cmd --list-all
```

References: `man firewall-cmd`.
