#!/usr/bin/env bash
student_write maintenance.yml <<YML
---
- name: Maintenance-aware changes
  hosts: all
  tasks:
    - name: Maintenance flag
      ansible.builtin.stat:
        path: /etc/lab-maintenance
      register: flag

    - name: Stop here for hosts in maintenance
      ansible.builtin.meta: end_host
      when: flag.stat.exists

    - name: Package
      ansible.builtin.dnf:
        name: $P_PKG
        state: present

    - name: Marker
      ansible.builtin.copy:
        content: "done\n"
        dest: /etc/lab-maintained
        mode: "0644"
YML
as_student ansible-playbook maintenance.yml
