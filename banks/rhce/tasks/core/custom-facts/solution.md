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

With **smart gathering and a fact cache** (`gathering = smart`, `fact_caching = jsonfile`), a play
doesn't gather facts a host already has in the cache, so a fact file added later stays invisible
until the cache expires. Run `ansible.builtin.setup` explicitly in the play, or the playbook with
`--flush-cache`.

References: Ansible docs *Discovering variables* (Adding custom facts).
