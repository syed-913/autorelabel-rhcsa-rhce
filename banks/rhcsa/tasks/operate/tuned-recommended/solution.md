## Recommended tuned profile

```bash
systemctl enable --now tuned
tuned-adm recommend            # virtual-guest in a VM
tuned-adm profile virtual-guest   # or: tuned-adm auto_profile
tuned-adm active
```

References: `man tuned-adm`.
