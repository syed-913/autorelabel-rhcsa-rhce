#!/usr/bin/env bash
student_write vars/tools.yml <<YML
---
tools:
  - $P_PKGS_0
  - $P_PKGS_1
YML
student_write tools.yml <<'YML'
---
- name: Install the tools
  hosts: test
  vars_files:
    - vars/tools.yml
  tasks:
    - name: Install the packages
      ansible.builtin.dnf:
        name: "{{ tools }}"
        state: present
    - name: List them
      ansible.builtin.copy:
        content: "{{ tools | join('\n') }}\n"
        dest: /etc/tools.list
        mode: "0644"
YML
as_student ansible-playbook tools.yml
