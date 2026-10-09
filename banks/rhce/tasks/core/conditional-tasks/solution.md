## when

```yaml
---
- name: Conditional tasks
  hosts: all
  tasks:
    - ansible.builtin.copy:
        content: "development\n"
        dest: /etc/lab-role
      when: "'dev' in group_names"                    # groups of the current host

    - ansible.builtin.copy:
        content: "production\n"
        dest: /etc/lab-role
      when: inventory_hostname in groups['prod']      # members of a group

    - ansible.builtin.copy:
        content: "large\n"
        dest: /etc/memory-class
      when: ansible_facts['memtotal_mb'] >= {{mem}}

    - ansible.builtin.copy:
        content: "small\n"
        dest: /etc/memory-class
      when: ansible_facts['memtotal_mb'] < {{mem}}
```

`when` is a raw Jinja2 expression: no `{{ }}` around it. Quote it when it starts with a
quote character. Facts are numbers already; compare them with numbers.

References: Ansible docs *Conditionals*.
