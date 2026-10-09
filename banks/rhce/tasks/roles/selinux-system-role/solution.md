## The selinux system role

```yaml
---
- name: SELinux settings
  hosts: dev
  pre_tasks:
    - ansible.builtin.file:
        path: {{dir}}
        state: directory
        mode: "0755"
  vars:
    selinux_state: enforcing
    selinux_policy: targeted
    selinux_booleans:
      - { name: httpd_can_network_connect, state: true, persistent: true }
    selinux_fcontexts:
      - { target: "{{dir}}(/.*)?", setype: httpd_sys_content_t, state: present }
    selinux_restore_dirs:
      - {{dir}}                         # runs restorecon -R on it
    selinux_ports:
      - { ports: "{{port}}", proto: tcp, setype: http_port_t, state: present }
  roles:
    - rhel-system-roles.selinux
```

`pre_tasks` run before the play's roles, so the directory exists when the role restores it.
Every variable is documented in `/usr/share/doc/rhel-system-roles/selinux/README.md`.

References: the role's README.md; RHEL 10 *Automating system administration by using RHEL system roles*.
