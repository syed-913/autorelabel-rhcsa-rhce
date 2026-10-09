## Packages and groups

```yaml
---
- name: Common packages
  hosts: dev,test,prod
  tasks:
    - ansible.builtin.dnf:
        name: [php, mariadb]          # one transaction for the list
        state: present

- name: Development hosts
  hosts: dev
  tasks:
    - ansible.builtin.dnf:
        name: "@RPM Development Tools"   # @ marks a group (or an environment group)
        state: present
    - ansible.builtin.dnf:
        name: "*"
        state: latest
```

`dnf group list` shows group names; `dnf group info "RPM Development Tools"` its packages.

References: `ansible-doc ansible.builtin.dnf`.
