#!/usr/bin/env bash
# Common mistake: owner, group and mode left to the defaults.
student_write deploy-files.yml <<YML
---
- name: Deploy application files
  hosts: prod
  tasks:
    - ansible.builtin.file: {path: /etc/$P_APP, state: directory}
    - ansible.builtin.copy: {src: files/app.conf, dest: /etc/$P_APP/app.conf}
    - ansible.builtin.copy:
        content: "Managed by Ansible - do not edit\n"
        dest: /etc/$P_APP/README
YML
as_student ansible-playbook deploy-files.yml
