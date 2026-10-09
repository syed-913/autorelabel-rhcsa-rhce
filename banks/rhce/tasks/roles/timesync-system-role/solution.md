## The timesync system role

```bash
ls /usr/share/ansible/roles/                         # rhel-system-roles.timesync, ...
less /usr/share/doc/rhel-system-roles/timesync/README.md
```

```yaml
---
- name: Time synchronization
  hosts: all
  vars:
    timesync_ntp_servers:
      - hostname: {{lab.ntp_server}}
        iburst: true
  roles:
    - rhel-system-roles.timesync          # or redhat.rhel_system_roles.timesync
```

The legacy name `rhel-system-roles.timesync` is found through `roles_path`
(`/usr/share/ansible/roles`). The collection name `redhat.rhel_system_roles.timesync` needs
`/usr/share/ansible/collections` in `collections_path`.

Check on a node: `chronyc sources -v`.

References: the role's README.md; RHEL 10 *Automating system administration by using RHEL system roles*.
