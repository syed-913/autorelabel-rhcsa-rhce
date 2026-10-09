#!/usr/bin/env bash
student_write cron.yml <<YML
---
- name: Heartbeat
  hosts: test
  tasks:
    - name: User
      ansible.builtin.user:
        name: $P_USER
    - name: Cron job
      ansible.builtin.cron:
        name: lab heartbeat
        user: $P_USER
        minute: "*/$P_EVERY"
        job: logger "EX294 heartbeat"
YML
as_student ansible-playbook cron.yml
