#!/usr/bin/env bash
# Common mistake: minute set to the number itself (runs once an hour at that minute).
student_write cron.yml <<YML
---
- name: Heartbeat
  hosts: test
  tasks:
    - ansible.builtin.user: {name: $P_USER}
    - ansible.builtin.cron:
        name: lab heartbeat
        user: $P_USER
        minute: "$P_EVERY"
        job: logger "EX294 heartbeat"
YML
as_student ansible-playbook cron.yml
