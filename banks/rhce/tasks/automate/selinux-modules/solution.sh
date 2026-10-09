#!/usr/bin/env bash
student_write selinux-settings.yml <<YML
---
- name: SELinux settings
  hosts: test
  tasks:
    - name: Enforcing
      ansible.posix.selinux:
        policy: targeted
        state: enforcing
    - name: Boolean
      ansible.posix.seboolean:
        name: $P_BOOL
        state: true
        persistent: true
    - name: Directory
      ansible.builtin.file:
        path: $P_DIR
        state: directory
        mode: "0755"
    - name: File context rule
      community.general.sefcontext:
        target: "$P_DIR(/.*)?"
        setype: public_content_t
        state: present
    - name: Apply it
      ansible.builtin.command: restorecon -Rv $P_DIR
      register: restore
      changed_when: restore.stdout | length > 0
    - name: Port
      community.general.seport:
        ports: "$P_PORT"
        proto: tcp
        setype: ssh_port_t
        state: present
YML
as_student ansible-playbook selinux-settings.yml
