## Ending the play for some hosts

```yaml
---
- name: Maintenance-aware changes
  hosts: all
  tasks:
    - ansible.builtin.stat:
        path: /etc/lab-maintenance
      register: flag

    - ansible.builtin.meta: end_host      # this host stops here, without failing
      when: flag.stat.exists

    - ansible.builtin.dnf:
        name: {{pkg}}
    - ansible.builtin.copy:
        content: "done\n"
        dest: /etc/lab-maintained
```

Alternatives: put the remaining tasks in a `block` with `when: not flag.stat.exists`, or use
`ansible.builtin.fail` to deliberately fail a host (that would mark the run as failed).

References: `ansible-doc ansible.builtin.meta`; Ansible docs *Conditionals*.
