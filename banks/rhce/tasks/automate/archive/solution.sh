#!/usr/bin/env bash
student_write archive.yml <<YML
---
- name: Back up sysconfig
  hosts: prod
  tasks:
    - name: Archive
      community.general.archive:
        path: /etc/sysconfig
        dest: /root/sysconfig.tar.gz
        format: gz

- name: Deploy the site
  hosts: dev
  tasks:
    - name: Directory
      ansible.builtin.file:
        path: /srv/site
        state: directory
        mode: "0755"
    - name: Extract
      ansible.builtin.unarchive:
        src: http://$LAB_UTILITY_FQDN/ansible/files/site-$P_WORD.tar.gz
        dest: /srv/site
        remote_src: true
YML
as_student ansible-playbook archive.yml
