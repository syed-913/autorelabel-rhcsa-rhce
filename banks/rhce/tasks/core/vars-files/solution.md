## vars_files

`~/ansible/vars/tools.yml`:

```yaml
---
tools:
  - {{pkgs.0}}
  - {{pkgs.1}}
```

`~/ansible/tools.yml`:

```yaml
---
- name: Install the tools
  hosts: test
  vars_files:
    - vars/tools.yml           # relative to the playbook
  tasks:
    - name: Install the packages
      ansible.builtin.dnf:
        name: "{{ tools }}"     # dnf takes a list: one transaction
        state: present
    - name: List them
      ansible.builtin.copy:
        content: "{{ tools | join('\n') }}\n"
        dest: /etc/tools.list
```

References: Ansible docs *Using variables* (vars_files); `ansible-doc ansible.builtin.dnf`.
