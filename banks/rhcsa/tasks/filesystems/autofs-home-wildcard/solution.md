## Network home directories with autofs

```bash
dnf install -y autofs nfs-utils
echo '/{{base}} /etc/auto.{{base}}' > /etc/auto.master.d/{{base}}.autofs
echo '* -rw,sync {{lab.nfs_server}}:/exports/{{base}}/&' > /etc/auto.{{base}}
systemctl enable --now autofs
su - {{user1}}; pwd; ls       # the home directory is mounted on login
```

`*` is any key (the user name) and `&` puts that key into the server path, so new users work
without editing the map.

References: RHEL 10 *Configuring and using network file services* → autofs; `man 5 autofs`.
