#!/usr/bin/env bash
# Common mistake: the else branch is missing, and test/balancer hosts get a role file too.
student_write conditions.yml <<YML
---
- name: Conditional tasks
  hosts: all
  tasks:
    - ansible.builtin.copy:
        content: "{{ 'development' if 'dev' in group_names else 'production' }}\n"
        dest: /etc/lab-role
    - ansible.builtin.copy:
        content: "large\n"
        dest: /etc/memory-class
      when: ansible_facts['memtotal_mb'] >= $P_MEM
YML
as_student ansible-playbook conditions.yml
