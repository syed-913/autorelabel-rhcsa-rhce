#!/usr/bin/env bash
student_write deploy-files.yml <<YML
---
- name: Deploy application files
  hosts: prod
  tasks:
    - name: Directory
      ansible.builtin.file:
        path: /etc/$P_APP
        state: directory
        mode: "0755"
    - name: Configuration
      ansible.builtin.copy:
        src: files/app.conf
        dest: /etc/$P_APP/app.conf
        owner: root
        group: $P_GRP
        mode: "0640"
    - name: README
      ansible.builtin.copy:
        content: "Managed by Ansible - do not edit\n"
        dest: /etc/$P_APP/README
        owner: root
        group: root
        mode: "0644"
YML
as_student ansible-playbook deploy-files.yml
