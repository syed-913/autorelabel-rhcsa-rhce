## Add a static IPv6 address

```bash
nmcli device                                     # connection on {{lab.node2.nic}}
nmcli connection modify <conn> +ipv6.addresses {{lab.ipv6_prefix}}{{host}}/64
nmcli connection up <conn>
ip -6 addr show {{lab.node2.nic}}
```

`+ipv6.addresses` **adds**; without the `+` the list is **replaced**.

References: RHEL 10 *Configuring and managing networking*; `man nmcli`.
