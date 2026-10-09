#!/usr/bin/env bash
# Valid alternative: a requirements file.
student_write collections/requirements.yml <<REQ
---
collections:
  - name: $LAB_COLLECTIONS_URL/ansible-posix.tar.gz
    type: url
  - name: $LAB_COLLECTIONS_URL/community-general.tar.gz
    type: url
REQ
as_student ansible-galaxy collection install -r collections/requirements.yml -p /home/student/ansible/mycollections
