#!/usr/bin/env bash
# Common mistake: the restricted port opened to everybody, and nothing made permanent.
student_write firewall.yml <<YML
---
- name: Firewall
  hosts: dev
  tasks:
    - ansible.posix.firewalld: {service: $P_SVC, immediate: true, state: enabled}
    - ansible.posix.firewalld: {port: $P_PORT/tcp, immediate: true, state: enabled}
    - ansible.posix.firewalld: {port: $P_RPORT/tcp, permanent: true, immediate: true, state: enabled}
YML
as_student ansible-playbook firewall.yml
