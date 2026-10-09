#!/usr/bin/env bash
# Valid alternative: decide from the free space fact instead of block/rescue.
student_write lv.yml <<YML
---
- name: Logical volumes
  hosts: all
  tasks:
    - ansible.builtin.debug: {msg: Volume group does not exist}
      when: ansible_lvm.vgs.research is not defined
    - ansible.builtin.debug: {msg: Could not create a logical volume of that size}
      when: ansible_lvm.vgs.research is defined and (ansible_lvm.vgs.research.free_g | float) * 1024 < $P_BIG
    - community.general.lvol:
        vg: research
        lv: data
        size: "{{ '${P_BIG}m' if (ansible_lvm.vgs.research.free_g | float) * 1024 >= $P_BIG else '${P_SMALL}m' }}"
      when: ansible_lvm.vgs.research is defined
    - community.general.filesystem: {fstype: ext4, dev: /dev/research/data}
      when: ansible_lvm.vgs.research is defined
YML
as_student ansible-playbook lv.yml
