#!/usr/bin/env bash
student_write issue.yml <<'YML'
---
- name: Login message per environment
  hosts: dev,test,prod
  tasks:
    - name: Development
      ansible.builtin.copy:
        content: "Development\n"
        dest: /etc/issue
      when: "'dev' in group_names"
    - name: Test
      ansible.builtin.copy:
        content: "Test\n"
        dest: /etc/issue
      when: "'test' in group_names"
    - name: Production
      ansible.builtin.copy:
        content: "Production\n"
        dest: /etc/issue
      when: "'prod' in group_names"
YML
as_student ansible-playbook issue.yml
