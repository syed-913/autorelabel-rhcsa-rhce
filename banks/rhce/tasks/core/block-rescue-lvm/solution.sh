#!/usr/bin/env bash
student_write lv.yml <<YML
---
- name: Logical volumes
  hosts: all
  tasks:
    - name: Volume group missing
      ansible.builtin.debug:
        msg: Volume group does not exist
      when: "'research' not in ansible_facts['lvm']['vgs']"

    - name: Logical volume and file system
      when: "'research' in ansible_facts['lvm']['vgs']"
      block:
        - name: Logical volume of $P_BIG MiB
          community.general.lvol:
            vg: research
            lv: data
            size: ${P_BIG}m
      rescue:
        - name: Not enough space
          ansible.builtin.debug:
            msg: Could not create a logical volume of that size
        - name: Logical volume of $P_SMALL MiB
          community.general.lvol:
            vg: research
            lv: data
            size: ${P_SMALL}m
      always:
        - name: ext4
          community.general.filesystem:
            fstype: ext4
            dev: /dev/research/data
YML
as_student ansible-playbook lv.yml
