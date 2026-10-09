#!/usr/bin/env bash
# Common mistake: relying on the exit status, so nothing ever fails.
student_write health.yml <<'YML'
---
- name: Health check
  hosts: all
  tasks:
    - ansible.builtin.command: /usr/local/bin/labcheck
      register: check
      changed_when: false
    - ansible.builtin.copy:
        content: "{{ 'FAIL' if check.rc != 0 else 'PASS' }}\n"
        dest: /etc/labcheck.status
YML
as_student ansible-playbook health.yml
