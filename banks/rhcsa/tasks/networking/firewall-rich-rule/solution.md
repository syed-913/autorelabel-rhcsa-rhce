## Allow a service for one source

```bash
firewall-cmd --permanent --add-rich-rule='rule family=ipv4 source address={{lab.node1.ip}}/32 service name=http accept'
firewall-cmd --reload
firewall-cmd --list-rich-rules
# test: from node1 → curl http://{{lab.node2.ip}}/ ; from the host/utility it must fail
```

Alternative: a zone bound to the source (`--new-zone`, `--add-source={{lab.node1.ip}}/32`,
`--add-service=http`). Traffic from that source then uses that zone.

**Classic mistake:** `--add-service=http` in the default zone (open to everyone).

References: RHEL 10 *Configuring firewalls and packet filters* → rich rules; `man firewalld.richlanguage`.
