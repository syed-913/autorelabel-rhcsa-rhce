#!/usr/bin/env bash
# Valid alternative: the roles: form of the requirements file, and the variables as play vars.
student_write roles/requirements.yml <<YML
---
roles:
  - name: motd
    src: $LAB_ROLES_URL/lab_motd.tar.gz
YML
as_student ansible-galaxy install -r roles/requirements.yml -p /home/student/ansible/roles
student_write motd.yml <<YML
---
- name: Login notice
  hosts: all
  vars:
    motd_message: $P_MSG
    motd_path: /etc/motd.d/lab-notice
  roles:
    - motd
YML
as_student ansible-playbook motd.yml
