## register

```yaml
---
- name: System status
  hosts: all
  tasks:
    - ansible.builtin.command: findmnt -no SOURCE /
      register: rootdev
      changed_when: false          # a read-only command
    - ansible.builtin.command: uname -r
      register: kernel
      changed_when: false
    - ansible.builtin.copy:
        content: |
          ROOT_DEVICE={{ rootdev.stdout }}
          KERNEL={{ kernel.stdout }}
        dest: /root/status.txt
```

A registered result is a dictionary: `stdout`, `stdout_lines`, `stderr`, `rc`, `changed`, ...
Look at it with `- ansible.builtin.debug: var=rootdev`.

References: Ansible docs *Registering variables*.
