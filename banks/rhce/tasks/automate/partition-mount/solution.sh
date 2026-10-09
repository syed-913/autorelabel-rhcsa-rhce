#!/usr/bin/env bash
student_write partition.yml <<YML
---
- name: Data partition
  hosts: dev
  tasks:
    - name: Partition
      community.general.parted:
        device: $LAB_NODE1_DISK1
        number: 1
        state: present
        part_end: ${P_SIZE}MiB
    - name: File system
      community.general.filesystem:
        fstype: $P_FS
        dev: ${LAB_NODE1_DISK1}1
    - name: Mount
      ansible.posix.mount:
        path: $P_MNT
        src: ${LAB_NODE1_DISK1}1
        fstype: $P_FS
        state: mounted
YML
as_student ansible-playbook partition.yml
