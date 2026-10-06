## Control services at boot

```bash
systemctl enable --now rsyslog                    # enable = at boot, --now = also start it
systemctl mask --now {{word}}-agent.service       # links the unit to /dev/null: cannot start
systemctl status {{word}}-agent.service           # "masked"
```

`disable` only removes the boot-time links. The unit can still be started by hand or as a
dependency. `mask` prevents that completely (undo with `unmask`).

References: RHEL 10 *Using systemd unit files* → managing services; `man systemctl`.
