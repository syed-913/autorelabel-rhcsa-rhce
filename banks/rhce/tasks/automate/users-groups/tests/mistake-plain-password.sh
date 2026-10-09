#!/usr/bin/env bash
# Common mistake: the clear-text password passed to the user module (stored as-is, not hashed).
student_write users.yml <<YML
---
- name: Users and groups
  hosts: all
  tasks:
    - ansible.builtin.group: {name: $P_GRP, gid: $P_GID}
    - ansible.builtin.user:
        name: "{{ item.name }}"
        uid: "{{ item.uid }}"
        groups: $P_GRP
        shell: "{{ item.shell }}"
        password: "Lab-$P_PW"
      loop:
        - { name: $P_U1, uid: 3101, shell: /bin/bash }
        - { name: $P_U2, uid: 3102, shell: /sbin/nologin }
YML
as_student ansible-playbook users.yml
