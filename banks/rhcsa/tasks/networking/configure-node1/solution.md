## Configure networking on node1

node1 has no IP address, so connect to its **console** (`./autorelabel console node1`), log in as
root with the password from the exam instructions, and use NetworkManager. `nmcli` creates a
persistent connection profile (a keyfile in `/etc/NetworkManager/system-connections/`):

```bash
nmcli device                                  # find the lab interface: {{lab.node1.nic}}
nmcli connection add type ethernet con-name {{lab.node1.nic}} ifname {{lab.node1.nic}} \
  ipv4.method manual ipv4.addresses {{lab.node1.ip}}/{{lab.prefix}} \
  ipv4.gateway {{lab.gateway}} ipv4.dns {{lab.dns}} connection.autoconnect yes
nmcli connection up {{lab.node1.nic}}
hostnamectl set-hostname {{lab.node1.fqdn}}
```

If a `Wired connection 1` profile already exists for the device, you can modify it instead with
`nmcli connection modify "Wired connection 1" ...`. `nmtui` is a menu-driven alternative that
writes the same profile.

Verify: `ip -br addr`, `ip route`, `cat /etc/resolv.conf`, `hostnamectl`, `ping {{lab.utility_fqdn}}`.

**Classic mistakes (both lose points after the grading reboot):**
- `ip addr add`, `hostname <name>` or editing `/etc/resolv.conf` by hand: runtime-only. NetworkManager
  rewrites `/etc/resolv.conf` and the address disappears at reboot.
- `connection.autoconnect no`: the profile exists but never activates at boot.

References: RHEL 10 *Configuring and managing networking* (Ethernet connections with nmcli);
`man nmcli-examples`, `man hostnamectl`.
