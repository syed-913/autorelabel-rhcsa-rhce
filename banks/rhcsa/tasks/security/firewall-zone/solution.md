## Default firewall zone

```bash
firewall-cmd --get-default-zone; firewall-cmd --get-active-zones
firewall-cmd --set-default-zone={{zone}}          # persistent by itself
firewall-cmd --permanent --zone={{zone}} --add-service=https
firewall-cmd --permanent --zone={{zone}} --add-service=ssh   # already there for most zones
firewall-cmd --reload
firewall-cmd --zone={{zone}} --list-all
```

Interfaces without an explicit zone use the default zone. (In this lab, `mgmt0` is pinned to
`trusted`; leave it alone.)

**Classic mistake:** adding the service without `--zone`, so it goes to whatever zone was the
default when you typed the command, or forgetting `--permanent`.

References: RHEL 10 *Configuring firewalls and packet filters* → zones; `man firewalld.zones`.
