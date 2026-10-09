## failed_when / changed_when

```yaml
---
- name: Health check
  hosts: all
  tasks:
    - name: Run labcheck
      ansible.builtin.command: /usr/local/bin/labcheck
      register: check
      failed_when: "'CRITICAL' in check.stdout"   # replaces the rc-based rule
      changed_when: false                         # a read-only command
      ignore_errors: true                         # keep the host in the play

    - name: Record the result
      ansible.builtin.copy:
        content: "{{ 'FAIL' if check is failed else 'PASS' }}\n"
        dest: /etc/labcheck.status
```

Without `ignore_errors` (or a block/rescue) the failed host would leave the play before the
second task. `is failed` / `is succeeded` test a registered result.

References: Ansible docs *Error handling in playbooks*.
