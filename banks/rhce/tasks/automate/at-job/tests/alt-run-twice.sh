#!/usr/bin/env bash
# Valid alternative: the same playbook run twice (unique keeps it at one job), with the module
# under its short name.
student_write at-job.yml <<YML
---
- name: One-time job
  hosts: dev
  tasks:
    - ansible.builtin.dnf: {name: at}
    - ansible.builtin.systemd_service: {name: atd, state: started, enabled: true}
    - at:
        command: logger lab-at-$P_WORD
        count: $P_DAYS
        units: days
        unique: true
YML
as_student ansible-playbook at-job.yml
as_student ansible-playbook at-job.yml
