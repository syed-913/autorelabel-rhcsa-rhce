#!/usr/bin/env bash
student_write sysctl.yml <<YML
---
- name: Kernel parameter
  hosts: all
  tasks:
    - name: Set $P_KP_KEY
      ansible.posix.sysctl:
        name: $P_KP_KEY
        value: "$P_KP_VALUE"
        sysctl_file: /etc/sysctl.d/90-lab.conf
        state: present
        reload: true
YML
as_student ansible-playbook sysctl.yml
