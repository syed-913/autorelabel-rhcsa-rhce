#!/usr/bin/env bash
student_write health.yml <<'YML'
---
- name: Health check
  hosts: all
  tasks:
    - name: Run labcheck
      ansible.builtin.command: /usr/local/bin/labcheck
      register: check
      failed_when: "'CRITICAL' in check.stdout"
      changed_when: false
      ignore_errors: true

    - name: Record the result
      ansible.builtin.copy:
        content: "{{ 'FAIL' if check is failed else 'PASS' }}\n"
        dest: /etc/labcheck.status
        mode: "0644"
YML
as_student ansible-playbook health.yml
