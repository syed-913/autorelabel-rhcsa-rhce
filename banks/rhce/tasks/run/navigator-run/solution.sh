#!/usr/bin/env bash
student_write ee-run.yml <<YML
---
- name: Install from the execution environment
  hosts: test
  tasks:
    - name: Package
      ansible.builtin.dnf:
        name: $P_PKG
        state: present
    - name: Marker
      ansible.builtin.copy:
        content: "installed by ansible\n"
        dest: /etc/ee-run
        mode: "0644"
YML
runuser -u student -- mkdir -p /home/student/ansible/artifacts
as_student ansible-navigator run ee-run.yml -m stdout --eei "$LAB_EE_IMAGE" --pp missing \
  --pae true --pas /home/student/ansible/artifacts/ee-run.json
as_student ansible-playbook ee-run.yml
