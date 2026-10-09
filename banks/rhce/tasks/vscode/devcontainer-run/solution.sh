#!/usr/bin/env bash
student_write ee-proof.yml <<'YML'
---
- name: Prove the run happened inside the container
  hosts: dev
  tasks:
    - name: Record the controller's container variable
      ansible.builtin.copy:
        content: "{{ lookup('ansible.builtin.env', 'container') }}\n"
        dest: /etc/ee-proof
        mode: "0644"
YML
as_student ansible-navigator run ee-proof.yml -m stdout --eei "$LAB_EE_IMAGE" --pp missing --pae false
