#!/usr/bin/env bash
# Common mistake: sefcontext alone (the rule exists, the directory keeps its old label) and a
# runtime-only boolean.
student_write selinux-settings.yml <<YML
---
- name: SELinux settings
  hosts: test
  tasks:
    - ansible.posix.selinux: {policy: targeted, state: enforcing}
    - ansible.posix.seboolean: {name: $P_BOOL, state: true}
    - ansible.builtin.file: {path: $P_DIR, state: directory}
    - community.general.sefcontext: {target: "$P_DIR(/.*)?", setype: public_content_t}
    - community.general.seport: {ports: "$P_PORT", proto: tcp, setype: ssh_port_t}
YML
as_student ansible-playbook selinux-settings.yml
