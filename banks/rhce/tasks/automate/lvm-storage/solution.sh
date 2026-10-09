#!/usr/bin/env bash
student_write lvm.yml <<YML
---
- name: LVM storage
  hosts: test
  tasks:
    - name: LVM partition
      community.general.parted:
        device: $LAB_NODE2_DISK1
        number: 1
        state: present
        part_end: 1500MiB
        flags: [lvm]
    - name: Volume group
      community.general.lvg:
        vg: $P_VG
        pvs: ${LAB_NODE2_DISK1}1
    - name: Logical volume
      community.general.lvol:
        vg: $P_VG
        lv: $P_LV
        size: ${P_SIZE}m
    - name: File system
      community.general.filesystem:
        fstype: ext4
        dev: /dev/$P_VG/$P_LV
    - name: Mount
      ansible.posix.mount:
        path: /mnt/$P_LV
        src: /dev/$P_VG/$P_LV
        fstype: ext4
        state: mounted
YML
as_student ansible-playbook lvm.yml
