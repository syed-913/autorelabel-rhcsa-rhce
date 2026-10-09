#!/usr/bin/env bash
# Common mistake: debug-shell "disabled" instead of masked, and the service started but not enabled.
pkg="$P_SVC"; [ "$P_SVC" = nfs-server ] && pkg=nfs-utils
student_write services.yml <<YML
---
- name: Services
  hosts: test
  tasks:
    - ansible.builtin.dnf: {name: $pkg}
    - ansible.builtin.systemd_service: {name: $P_SVC, state: started}
    - ansible.builtin.systemd_service: {name: debug-shell.service, enabled: false}
    - ansible.builtin.command: systemctl set-default multi-user.target
YML
as_student ansible-playbook services.yml
