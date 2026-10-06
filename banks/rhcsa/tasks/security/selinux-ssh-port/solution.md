## sshd on an additional port

```bash
semanage port -a -t ssh_port_t -p tcp {{port}}
cat > /etc/ssh/sshd_config.d/60-extra-port.conf <<'X'
Port 22
Port {{port}}
X
sshd -t                                        # syntax check before restarting!
firewall-cmd --permanent --add-port={{port}}/tcp; firewall-cmd --reload
systemctl restart sshd
ss -lntp | grep sshd
```

Listing `Port 22` explicitly matters: once any `Port` line exists, sshd listens **only** on the
ports listed.

References: `man sshd_config`, `man semanage-port`.
