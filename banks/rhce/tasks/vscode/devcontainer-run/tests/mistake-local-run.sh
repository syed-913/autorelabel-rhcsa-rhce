#!/usr/bin/env bash
# Common mistake: run with the local ansible-core (no container): the variable is empty.
student_write ee-proof.yml <<'YML'
---
- name: Prove the run happened inside the container
  hosts: dev
  tasks:
    - ansible.builtin.copy:
        content: "{{ lookup('ansible.builtin.env', 'container') }}\n"
        dest: /etc/ee-proof
YML
as_student ansible-playbook ee-proof.yml
