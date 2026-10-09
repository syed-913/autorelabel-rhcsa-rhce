#!/usr/bin/env bash
# Common mistake: size given as "g" (a GiB value) and the mount only in fstab.
student_write lvm.yml <<YML
---
- name: LVM storage
  hosts: test
  tasks:
    - community.general.parted: {device: $LAB_NODE2_DISK1, number: 1, state: present, part_end: 1500MiB, flags: [lvm]}
    - community.general.lvg: {vg: $P_VG, pvs: ${LAB_NODE2_DISK1}1}
    - community.general.lvol: {vg: $P_VG, lv: $P_LV, size: 1g}
    - community.general.filesystem: {fstype: ext4, dev: /dev/$P_VG/$P_LV}
    - ansible.posix.mount: {path: /mnt/$P_LV, src: /dev/$P_VG/$P_LV, fstype: ext4, state: present}
YML
as_student ansible-playbook lvm.yml
