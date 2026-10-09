#!/usr/bin/env bash
student_write status.yml <<'YML'
---
- name: System status
  hosts: all
  tasks:
    - name: Root device
      ansible.builtin.command: findmnt -no SOURCE /
      register: rootdev
      changed_when: false
    - name: Kernel
      ansible.builtin.command: uname -r
      register: kernel
      changed_when: false
    - name: Write the report
      ansible.builtin.copy:
        content: |
          ROOT_DEVICE={{ rootdev.stdout }}
          KERNEL={{ kernel.stdout }}
        dest: /root/status.txt
        mode: "0644"
YML
as_student ansible-playbook status.yml
