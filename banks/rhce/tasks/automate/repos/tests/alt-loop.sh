#!/usr/bin/env bash
# Valid alternative: one task with a loop, both repositories in a single file.
student_write repos.yml <<YML
---
- name: Configure the lab repositories
  hosts: all
  become: true
  tasks:
    - name: Lab repositories
      ansible.builtin.yum_repository:
        name: "{{ item.id }}"
        description: "RHEL 10 {{ item.id }}"
        file: lab
        baseurl: "{{ item.url }}"
        gpgcheck: yes
        gpgkey: $LAB_REPO_GPGKEY
      loop:
        - { id: BaseOS, url: "$LAB_REPO_BASEOS" }
        - { id: AppStream, url: "$LAB_REPO_APPSTREAM" }
YML
as_student ansible-playbook repos.yml
