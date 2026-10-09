#!/usr/bin/env bash
# Common mistake: a made-up variable name; the role silently keeps its defaults.
student_write timesync.yml <<YML
---
- name: Time synchronization
  hosts: all
  vars:
    ntp_servers:
      - $LAB_NTP_SERVER
  roles:
    - rhel-system-roles.timesync
YML
as_student ansible-playbook timesync.yml
