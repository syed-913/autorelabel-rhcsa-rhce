## group_vars and host_vars

Files next to the inventory (or the playbook) are loaded automatically:

```text
~/ansible/group_vars/dev.yml                       {{var}}: development
~/ansible/group_vars/test.yml                      {{var}}: testing
~/ansible/group_vars/prod.yml                      {{var}}: production
~/ansible/host_vars/node3.lab.example.com.yml      {{var}}: production-primary
```

The `host_vars` file name must match the **inventory host name** exactly (FQDN here). Host
variables beat group variables, so node3 gets `production-primary`.

```yaml
---
- name: Record the environment
  hosts: dev,test,prod
  tasks:
    - name: Write /etc/lab-environment
      ansible.builtin.copy:
        content: "ENVIRONMENT={{ {{var}} }}\n"
        dest: /etc/lab-environment
```

Verify with `ansible-inventory --host node3.lab.example.com` or `ansible-inventory --graph --vars`.

References: Ansible docs *Organizing host and group variables*, *Variable precedence*.
