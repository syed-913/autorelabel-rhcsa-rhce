## Web server on a non-standard port

Diagnose:

```bash
systemctl status httpd                 # "Permission denied: AH00072: make_sock: could not bind"
ausearch -m AVC -ts recent             # name_bind denied for port {{port}}
semanage port -l | grep http_port_t    # {{port}} is not in the list
```

Fix all three layers:

```bash
semanage port -a -t http_port_t -p tcp {{port}}     # SELinux: allow httpd to bind it
firewall-cmd --permanent --add-port={{port}}/tcp    # firewall: allow remote access
firewall-cmd --reload
systemctl enable --now httpd                         # running now and at boot
curl http://{{lab.node2.fqdn}}:{{port}}/             # test from node1 or the host
```

**Classic mistakes:** a firewall rule without `--permanent`; opening the `http` service (that is
port 80, not {{port}}); `systemctl start` without `enable`; `setenforce 0` instead of labelling
the port.

References: RHEL 10 *Using SELinux* (non-standard configurations); *Configuring firewalls and
packet filters*; `man semanage-port`.
