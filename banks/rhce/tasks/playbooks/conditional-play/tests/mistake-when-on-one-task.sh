#!/usr/bin/env bash
# Common mistake: the condition only on the package task; the marker is still written.
student_write maintenance.yml <<YML
---
- name: Maintenance-aware changes
  hosts: all
  tasks:
    - ansible.builtin.stat: {path: /etc/lab-maintenance}
      register: flag
    - ansible.builtin.dnf: {name: $P_PKG}
      when: not flag.stat.exists
    - ansible.builtin.copy: {content: "done\n", dest: /etc/lab-maintained}
YML
as_student ansible-playbook maintenance.yml
