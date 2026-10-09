#!/usr/bin/env bash
# Common mistake: the group name without @ (treated as a package name), so the play fails there.
student_write packages.yml <<'YML'
---
- name: Common packages
  hosts: dev,test,prod
  tasks:
    - ansible.builtin.dnf: {name: [php, mariadb]}
- name: Development hosts
  hosts: dev
  ignore_errors: true
  tasks:
    - ansible.builtin.dnf: {name: "RPM Development Tools"}
    - ansible.builtin.dnf: {name: "*", state: latest}
YML
as_student ansible-playbook packages.yml || true
