#!/usr/bin/env bash
# Common mistake: without sysctl_file the module writes /etc/sysctl.conf.
student_write sysctl.yml <<YML
---
- name: Kernel parameter
  hosts: all
  tasks:
    - ansible.posix.sysctl:
        name: $P_KP_KEY
        value: "$P_KP_VALUE"
        reload: true
YML
as_student ansible-playbook sysctl.yml
