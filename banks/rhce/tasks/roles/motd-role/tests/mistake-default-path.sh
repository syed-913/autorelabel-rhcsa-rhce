#!/usr/bin/env bash
# Common mistake: only the message set; the role keeps its default path and overwrites /etc/motd.
student_write roles/requirements.yml <<YML
---
- src: $LAB_ROLES_URL/lab_motd.tar.gz
  name: motd
YML
as_student ansible-galaxy role install -r roles/requirements.yml -p roles
student_write motd.yml <<YML
---
- hosts: all
  roles:
    - {role: motd, motd_message: "$P_MSG"}
YML
as_student ansible-playbook motd.yml
