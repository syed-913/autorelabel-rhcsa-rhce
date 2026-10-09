#!/usr/bin/env bash
student_write repos.yml <<YML
---
- name: Configure the lab repositories
  hosts: all
  tasks:
    - name: BaseOS repository
      ansible.builtin.yum_repository:
        name: BaseOS
        description: RHEL 10 BaseOS
        baseurl: $LAB_REPO_BASEOS
        gpgcheck: true
        gpgkey: $LAB_REPO_GPGKEY
        enabled: true

    - name: AppStream repository
      ansible.builtin.yum_repository:
        name: AppStream
        description: RHEL 10 AppStream
        baseurl: $LAB_REPO_APPSTREAM
        gpgcheck: true
        gpgkey: $LAB_REPO_GPGKEY
        enabled: true
YML
as_student ansible-playbook repos.yml
