#!/usr/bin/env bash
# Common mistake: the image is named but the execution environment is switched off (the run
# uses the local ansible-core).
student_write ee-run.yml <<YML
---
- name: Install
  hosts: test
  tasks:
    - ansible.builtin.dnf: {name: $P_PKG}
    - ansible.builtin.copy: {content: "installed by ansible\n", dest: /etc/ee-run}
YML
runuser -u student -- mkdir -p /home/student/ansible/artifacts
as_student ansible-navigator run ee-run.yml -m stdout --eei "$LAB_EE_IMAGE" --ee false --pae true \
  --pas /home/student/ansible/artifacts/ee-run.json
