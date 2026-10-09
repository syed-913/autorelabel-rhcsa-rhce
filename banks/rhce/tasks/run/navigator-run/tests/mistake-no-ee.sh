#!/usr/bin/env bash
# Common mistake: execution environment switched off (runs with the local ansible-core).
student_write ee-run.yml <<YML
---
- name: Install
  hosts: test
  tasks:
    - ansible.builtin.dnf: {name: $P_PKG}
    - ansible.builtin.copy: {content: "installed by ansible\n", dest: /etc/ee-run}
YML
runuser -u student -- mkdir -p /home/student/ansible/artifacts
as_student ansible-navigator run ee-run.yml -m stdout --ee false --pae true \
  --pas /home/student/ansible/artifacts/ee-run.json
