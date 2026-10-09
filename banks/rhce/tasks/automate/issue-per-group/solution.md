## Content per group

```yaml
---
- name: Login message per environment
  hosts: dev,test,prod
  tasks:
    - ansible.builtin.copy:
        content: "Development\n"
        dest: /etc/issue
      when: "'dev' in group_names"
    - ansible.builtin.copy:
        content: "Test\n"
        dest: /etc/issue
      when: "'test' in group_names"
    - ansible.builtin.copy:
        content: "Production\n"
        dest: /etc/issue
      when: "'prod' in group_names"
```

`copy: content:` replaces the whole file; `lineinfile` only adds or edits one line in it.

References: `ansible-doc ansible.builtin.copy`.
