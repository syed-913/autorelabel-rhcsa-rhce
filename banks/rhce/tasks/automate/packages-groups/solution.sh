#!/usr/bin/env bash
student_write packages.yml <<'YML'
---
- name: Common packages
  hosts: dev,test,prod
  tasks:
    - name: php and mariadb
      ansible.builtin.dnf:
        name: [php, mariadb]
        state: present

- name: Development hosts
  hosts: dev
  tasks:
    - name: RPM Development Tools
      ansible.builtin.dnf:
        name: "@RPM Development Tools"
        state: present
    - name: Everything up to date
      ansible.builtin.dnf:
        name: "*"
        state: latest
YML
as_student ansible-playbook packages.yml
