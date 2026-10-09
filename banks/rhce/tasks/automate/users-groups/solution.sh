#!/usr/bin/env bash
student_write users.yml <<YML
---
- name: Users and groups
  hosts: all
  vars:
    lab_users:
      - { name: $P_U1, uid: 3101, shell: /bin/bash }
      - { name: $P_U2, uid: 3102, shell: /sbin/nologin }
  tasks:
    - name: Group
      ansible.builtin.group:
        name: $P_GRP
        gid: $P_GID
    - name: Users
      ansible.builtin.user:
        name: "{{ item.name }}"
        uid: "{{ item.uid }}"
        groups: $P_GRP
        append: true
        shell: "{{ item.shell }}"
        password: "{{ 'Lab-$P_PW' | password_hash('sha512') }}"
        update_password: always
      loop: "{{ lab_users }}"
YML
as_student ansible-playbook users.yml
