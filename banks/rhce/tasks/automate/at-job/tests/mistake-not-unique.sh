#!/usr/bin/env bash
# Common mistake: no unique, so the second run queues the job again (it would run twice).
student_write at-job.yml <<YML
---
- name: One-time job
  hosts: dev
  tasks:
    - ansible.builtin.dnf: {name: at}
    - ansible.builtin.service: {name: atd, state: started, enabled: true}
    - ansible.posix.at: {command: "logger lab-at-$P_WORD", count: $P_DAYS, units: days}
YML
as_student ansible-playbook at-job.yml
as_student ansible-playbook at-job.yml
