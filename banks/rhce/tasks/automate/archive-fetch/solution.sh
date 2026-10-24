#!/usr/bin/env bash
student_write collect.yml <<YML
---
- name: Collect configuration archives
  hosts: test
  tasks:
    - name: Archive $P_SRC_DIR
      community.general.archive:
        path: $P_SRC_DIR
        dest: /root/config.$P_FMT_EXT
        format: $P_FMT_NAME
        mode: "0600"
    - name: Copy it to control
      ansible.builtin.fetch:
        src: /root/config.$P_FMT_EXT
        dest: "/home/student/ansible/collected/{{ inventory_hostname_short }}.$P_FMT_EXT"
        flat: true
YML
as_student ansible-playbook collect.yml
