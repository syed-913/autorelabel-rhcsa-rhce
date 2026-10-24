#!/usr/bin/env bash
# Common mistake: the format left at its default (gzip) under the requested file name.
student_write collect.yml <<YML
---
- name: Collect configuration archives
  hosts: test
  tasks:
    - community.general.archive: {path: $P_SRC_DIR, dest: /root/config.$P_FMT_EXT}
    - ansible.builtin.fetch:
        src: /root/config.$P_FMT_EXT
        dest: "/home/student/ansible/collected/{{ inventory_hostname_short }}.$P_FMT_EXT"
        flat: true
YML
as_student ansible-playbook collect.yml
