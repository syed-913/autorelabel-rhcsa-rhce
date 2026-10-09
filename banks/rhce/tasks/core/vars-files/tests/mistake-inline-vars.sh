#!/usr/bin/env bash
# Common mistake: the list defined in the play with vars: instead of a vars file.
student_write tools.yml <<YML
---
- name: Install the tools
  hosts: test
  vars:
    tools: [$P_PKGS_0, $P_PKGS_1]
  tasks:
    - name: Install the packages
      ansible.builtin.dnf:
        name: "{{ tools }}"
    - name: List them
      ansible.builtin.copy:
        content: "{{ tools | join('\n') }}\n"
        dest: /etc/tools.list
YML
as_student ansible-playbook tools.yml
