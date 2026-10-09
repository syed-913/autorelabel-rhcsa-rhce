#!/usr/bin/env bash
# Common mistake: the whole registered dictionary written instead of .stdout.
student_write status.yml <<'YML'
---
- name: System status
  hosts: all
  tasks:
    - ansible.builtin.command: findmnt -no SOURCE /
      register: rootdev
    - ansible.builtin.command: uname -r
      register: kernel
    - ansible.builtin.copy:
        content: |
          ROOT_DEVICE={{ rootdev }}
          KERNEL={{ kernel }}
        dest: /root/status.txt
YML
as_student ansible-playbook status.yml
