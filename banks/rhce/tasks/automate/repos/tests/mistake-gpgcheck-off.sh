#!/usr/bin/env bash
# Common mistake: GPG checking disabled "to make it work".
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
        gpgcheck: false
    - name: AppStream repository
      ansible.builtin.yum_repository:
        name: AppStream
        description: RHEL 10 AppStream
        baseurl: $LAB_REPO_APPSTREAM
        gpgcheck: false
YML
as_student ansible-playbook repos.yml
