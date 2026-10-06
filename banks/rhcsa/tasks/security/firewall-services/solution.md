## Open services and ports

```bash
firewall-cmd --permanent --add-service={{service}}
firewall-cmd --permanent --add-port={{port}}/tcp
firewall-cmd --reload
firewall-cmd --list-all
```

`--permanent` writes the configuration; `--reload` applies it now. Alternatively make the runtime
change and save it with `firewall-cmd --runtime-to-permanent`.

**Classic mistake:** forgetting `--permanent`. The rule works until the reboot.

References: RHEL 10 *Configuring firewalls and packet filters*; `man firewall-cmd`.
