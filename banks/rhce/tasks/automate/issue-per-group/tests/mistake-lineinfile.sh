#!/usr/bin/env bash
# Common mistake: lineinfile appends a line instead of replacing the content.
student_write issue.yml <<'YML'
---
- name: Login message per environment
  hosts: dev,test,prod
  tasks:
    - ansible.builtin.lineinfile: {path: /etc/issue, line: Development}
      when: "'dev' in group_names"
    - ansible.builtin.lineinfile: {path: /etc/issue, line: Test}
      when: "'test' in group_names"
    - ansible.builtin.lineinfile: {path: /etc/issue, line: Production}
      when: "'prod' in group_names"
YML
as_student ansible-playbook issue.yml
