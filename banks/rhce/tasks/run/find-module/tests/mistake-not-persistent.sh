#!/usr/bin/env bash
# Common mistake: loaded now only (persistent defaults to disabled).
student_write kmod.yml <<YML
---
- name: Kernel module
  hosts: dev
  tasks:
    - community.general.modprobe:
        name: brd
        params: rd_nr=$P_NUM
        state: present
YML
as_student ansible-playbook kmod.yml
