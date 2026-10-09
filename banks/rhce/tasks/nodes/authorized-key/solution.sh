#!/usr/bin/env bash
runuser -u student -- ssh-keygen -q -t ed25519 -N '' -f "/home/student/.ssh/${P_USER}_key"
student_write deploy-user.yml <<YML
---
- name: Deploy user with key
  hosts: dev,test
  tasks:
    - name: User
      ansible.builtin.user:
        name: $P_USER
        state: present
    - name: Authorized key
      ansible.posix.authorized_key:
        user: $P_USER
        key: "{{ lookup('ansible.builtin.file', '/home/student/.ssh/${P_USER}_key.pub') }}"
        state: present
YML
as_student ansible-playbook deploy-user.yml
