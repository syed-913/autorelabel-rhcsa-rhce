#!/usr/bin/env bash
# Common mistake: the wrong unit (hours instead of days).
student_write at-job.yml <<YML
---
- name: One-time job
  hosts: dev
  tasks:
    - ansible.builtin.dnf: {name: at}
    - ansible.builtin.service: {name: atd, state: started, enabled: true}
    - ansible.posix.at: {command: "logger lab-at-$P_WORD", count: $P_DAYS, units: hours, unique: true}
YML
as_student ansible-playbook at-job.yml
