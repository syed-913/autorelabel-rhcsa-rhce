## Remove firewall openings

```bash
firewall-cmd --list-all
firewall-cmd --permanent --remove-service=cockpit --remove-service=dhcpv6-client
firewall-cmd --permanent --remove-port={{port}}/tcp       # can't be combined with --remove-service
firewall-cmd --reload
firewall-cmd --list-all
```

References: `man firewall-cmd`.
