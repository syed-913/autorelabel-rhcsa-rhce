#!/usr/bin/env bash
# Common mistake: state ephemeral (mounted now, no fstab entry).
student_write partition.yml <<YML
---
- name: Data partition
  hosts: dev
  tasks:
    - community.general.parted: {device: $LAB_NODE1_DISK1, number: 1, state: present, part_end: ${P_SIZE}MiB}
    - community.general.filesystem: {fstype: $P_FS, dev: ${LAB_NODE1_DISK1}1}
    - ansible.posix.mount: {path: $P_MNT, src: ${LAB_NODE1_DISK1}1, fstype: $P_FS, state: ephemeral}
YML
as_student ansible-playbook partition.yml
