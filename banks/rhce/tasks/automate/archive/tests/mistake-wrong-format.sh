#!/usr/bin/env bash
# Common mistake: the archive format left at a non-gzip choice (bz2 here) under a .tar.gz name.
student_write archive.yml <<YML
---
- name: Back up sysconfig
  hosts: prod
  tasks:
    - community.general.archive: {path: /etc/sysconfig, dest: /root/sysconfig.tar.gz, format: bz2}
- name: Deploy the site
  hosts: dev
  tasks:
    - ansible.builtin.file: {path: /srv/site, state: directory}
    - ansible.builtin.unarchive:
        src: http://$LAB_UTILITY_FQDN/ansible/files/site-$P_WORD.tar.gz
        dest: /srv/site
        remote_src: true
YML
as_student ansible-playbook archive.yml
