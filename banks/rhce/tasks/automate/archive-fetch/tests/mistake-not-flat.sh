#!/usr/bin/env bash
# Common mistake: fetch without flat, so every archive lands in collected/<host>/root/... instead.
student_write collect.yml <<YML
---
- name: Collect configuration archives
  hosts: test
  tasks:
    - community.general.archive: {path: $P_SRC_DIR, dest: /root/config.$P_FMT_EXT, format: $P_FMT_NAME}
    - ansible.builtin.fetch: {src: /root/config.$P_FMT_EXT, dest: /home/student/ansible/collected/}
YML
as_student ansible-playbook collect.yml
