#!/usr/bin/env bash
student_write at-job.yml <<YML
---
- name: One-time job
  hosts: dev
  tasks:
    - name: at
      ansible.builtin.dnf:
        name: at
        state: present
    - name: atd
      ansible.builtin.service:
        name: atd
        state: started
        enabled: true
    - name: Schedule the job
      ansible.posix.at:
        command: logger lab-at-$P_WORD
        count: $P_DAYS
        units: days
        unique: true
YML
as_student ansible-playbook at-job.yml
