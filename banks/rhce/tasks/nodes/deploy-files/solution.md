## copy with src and with content

```yaml
---
- name: Deploy application files
  hosts: prod
  tasks:
    - ansible.builtin.file:
        path: /etc/{{app}}
        state: directory
        mode: "0755"
    - ansible.builtin.copy:
        src: files/app.conf              # relative to the playbook (or a role's files/)
        dest: /etc/{{app}}/app.conf
        owner: root
        group: {{grp}}
        mode: "0640"
    - ansible.builtin.copy:
        content: "Managed by Ansible - do not edit\n"
        dest: /etc/{{app}}/README
        mode: "0644"
```

Without `mode`, new files get the remote umask's default (0644) and directories 0755.

References: `ansible-doc ansible.builtin.copy`.
