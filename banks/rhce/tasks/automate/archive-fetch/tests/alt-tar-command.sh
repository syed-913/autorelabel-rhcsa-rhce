#!/usr/bin/env bash
# Valid alternative: tar run as a command (with creates for idempotence), and fetch.
student_write collect.yml <<YML
---
- name: Collect configuration archives
  hosts: test
  tasks:
    - ansible.builtin.command:
        cmd: tar --$P_FMT_TOOL -cf /root/config.$P_FMT_EXT $P_SRC_DIR
        creates: /root/config.$P_FMT_EXT
    - ansible.builtin.fetch:
        src: /root/config.$P_FMT_EXT
        dest: "collected/{{ ansible_facts['hostname'] }}.$P_FMT_EXT"
        flat: true
YML
as_student ansible-playbook collect.yml
