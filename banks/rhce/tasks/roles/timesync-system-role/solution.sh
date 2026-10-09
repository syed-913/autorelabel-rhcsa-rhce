#!/usr/bin/env bash
student_write timesync.yml <<YML
---
- name: Time synchronization
  hosts: all
  vars:
    timesync_ntp_servers:
      - hostname: $LAB_NTP_SERVER
        iburst: true
  roles:
    - rhel-system-roles.timesync
YML
as_student ansible-playbook timesync.yml
