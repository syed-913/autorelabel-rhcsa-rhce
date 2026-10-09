## Users from a list

```yaml
---
- name: Users and groups
  hosts: all
  vars:
    lab_users:
      - { name: {{u1}}, uid: 3101, shell: /bin/bash }
      - { name: {{u2}}, uid: 3102, shell: /sbin/nologin }
  tasks:
    - ansible.builtin.group:
        name: {{grp}}
        gid: {{gid}}
    - ansible.builtin.user:
        name: "{{ item.name }}"
        uid: "{{ item.uid }}"
        groups: {{grp}}
        append: true                      # keep any other groups
        shell: "{{ item.shell }}"
        password: "{{ 'Lab-{{pw}}' | password_hash('sha512') }}"
      loop: "{{ lab_users }}"
```

`password:` expects a **hash**. A clear-text value is written to /etc/shadow as-is and no
password will ever match it.

References: `ansible-doc ansible.builtin.user`; Ansible docs *Filters* (password_hash).
