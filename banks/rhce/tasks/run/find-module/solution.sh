#!/usr/bin/env bash
student_write kmod.yml <<YML
---
- name: Kernel module
  hosts: dev
  tasks:
    - name: Load dummy now and at boot
      community.general.modprobe:
        name: dummy
        params: numdummies=$P_NUM
        state: present
        persistent: present
YML
as_student ansible-playbook kmod.yml
