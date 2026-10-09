#!/usr/bin/env bash
student_write conditions.yml <<YML
---
- name: Conditional tasks
  hosts: all
  tasks:
    - name: Development role
      ansible.builtin.copy:
        content: "development\n"
        dest: /etc/lab-role
      when: "'dev' in group_names"

    - name: Production role
      ansible.builtin.copy:
        content: "production\n"
        dest: /etc/lab-role
      when: inventory_hostname in groups['prod']

    - name: Memory class
      ansible.builtin.copy:
        content: "{{ 'large' if ansible_facts['memtotal_mb'] >= $P_MEM else 'small' }}\n"
        dest: /etc/memory-class
YML
as_student ansible-playbook conditions.yml
