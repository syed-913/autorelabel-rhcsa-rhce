#!/usr/bin/env bash
# Common mistake: the rule is added but never applied to the existing directory, and the
# boolean is not persistent.
student_write selinux.yml <<YML
---
- name: SELinux settings
  hosts: dev
  pre_tasks:
    - ansible.builtin.file: {path: $P_DIR, state: directory}
  vars:
    selinux_state: enforcing
    selinux_policy: targeted
    selinux_booleans:
      - {name: httpd_can_network_connect, state: true}
    selinux_fcontexts:
      - {target: "$P_DIR(/.*)?", setype: httpd_sys_content_t, state: present}
    selinux_ports:
      - {ports: "$P_PORT", proto: tcp, setype: http_port_t, state: present}
  roles:
    - rhel-system-roles.selinux
YML
as_student ansible-playbook selinux.yml
