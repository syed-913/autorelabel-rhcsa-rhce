#!/usr/bin/env bash
for c in ansible-posix community-general; do
  as_student ansible-galaxy collection install "$LAB_COLLECTIONS_URL/$c.tar.gz" -p /home/student/ansible/mycollections
done
