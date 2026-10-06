## Network connection at boot

```bash
nmcli connection show                                     # find the lab profile
nmcli -f connection.autoconnect connection show <conn>    # "no"
nmcli connection modify <conn> connection.autoconnect yes
nmcli connection up <conn>
```

**Classic mistake:** `nmcli connection up` alone. It works until the next reboot.

References: RHEL 10 *Configuring and managing networking*; `man nm-settings-nmcli`.
