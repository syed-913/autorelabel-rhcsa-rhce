## Default boot target

```bash
systemctl get-default                     # graphical.target
systemctl set-default multi-user.target   # persistent (a symlink: /etc/systemd/system/default.target)
```

`systemctl isolate multi-user.target` only switches the **running** system. It's how you change
targets manually, but it does not change what the next boot uses.

References: RHEL 10 *Using systemd unit files* → default target; `man systemctl`.
