## Custom facts

A file `/etc/ansible/facts.d/<name>.fact` on a managed node (INI, JSON, or an executable that
prints JSON) appears after fact gathering as `ansible_local['<name>']`:

```yaml
# custom-facts.yml
- name: Install the custom fact
  hosts: dev
  tasks:
    - ansible.builtin.file:
        path: /etc/ansible/facts.d
        state: directory
    - ansible.builtin.copy:
        dest: /etc/ansible/facts.d/lab.fact
        content: |
          [service]
          name={{svc}}
          port={{port}}
```

```yaml
# use-facts.yml
- name: Use the custom fact
  hosts: dev
  tasks:
    - ansible.builtin.copy:
        content: "SERVICE={{ ansible_local['lab']['service']['name'] }} PORT={{ ansible_local['lab']['service']['port'] }}\n"
        dest: /etc/lab-service
```

Check what Ansible sees: `ansible dev -m ansible.builtin.setup -a 'filter=ansible_local'`.
A fact file installed in the *same* play is only visible after `ansible.builtin.setup` runs again.

References: Ansible docs *Discovering variables* (Adding custom facts).
