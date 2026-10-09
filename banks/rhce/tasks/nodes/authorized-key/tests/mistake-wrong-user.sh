#!/usr/bin/env bash
# Common mistake: the key authorized for the ansible user (the connection user) instead.
runuser -u student -- ssh-keygen -q -t ed25519 -N '' -f "/home/student/.ssh/${P_USER}_key"
student_write deploy-user.yml <<YML
---
- name: Deploy user with key
  hosts: dev,test
  tasks:
    - ansible.builtin.user: {name: $P_USER}
    - ansible.posix.authorized_key:
        user: ansible
        key: "{{ lookup('ansible.builtin.file', '/home/student/.ssh/${P_USER}_key.pub') }}"
YML
as_student ansible-playbook deploy-user.yml
