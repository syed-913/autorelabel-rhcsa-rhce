#!/usr/bin/env bash
# Common mistake: no name in the requirements file, so the role is installed as lab_motd.
student_write roles/requirements.yml <<YML
---
- src: $LAB_ROLES_URL/lab_motd.tar.gz
YML
as_student ansible-galaxy role install -r roles/requirements.yml -p roles
student_write motd.yml <<YML
---
- hosts: all
  roles:
    - {role: lab_motd, motd_message: "$P_MSG", motd_path: /etc/motd.d/lab-notice}
YML
as_student ansible-playbook motd.yml
