#!/usr/bin/env bash
pkg="$P_SVC"; [ "$P_SVC" = nfs-server ] && pkg=nfs-utils
student_write services.yml <<YML
---
- name: Services
  hosts: test
  tasks:
    - name: Package
      ansible.builtin.dnf:
        name: $pkg
        state: present
    - name: $P_SVC
      ansible.builtin.systemd_service:
        name: $P_SVC
        state: started
        enabled: true
    - name: Mask debug-shell
      ansible.builtin.systemd_service:
        name: debug-shell.service
        masked: true
    - name: Default target
      ansible.builtin.file:
        src: /usr/lib/systemd/system/multi-user.target
        dest: /etc/systemd/system/default.target
        state: link
YML
as_student ansible-playbook services.yml
