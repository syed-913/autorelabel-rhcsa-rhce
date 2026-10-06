## Default target: graphical

```bash
systemctl set-default graphical.target
systemctl get-default
```

`systemctl isolate graphical.target` switches the running system only; `set-default` is persistent.

References: `man systemctl`.
