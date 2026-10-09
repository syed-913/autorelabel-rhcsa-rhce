#!/usr/bin/env bash
# Common mistake: no fallback; the host without enough space fails and gets nothing.
student_write lv.yml <<YML
---
- name: Logical volumes
  hosts: all
  ignore_unreachable: true
  tasks:
    - community.general.lvol: {vg: research, lv: data, size: ${P_BIG}m}
      when: "'research' in ansible_facts['lvm']['vgs']"
      ignore_errors: true
      register: lv
    - community.general.filesystem: {fstype: ext4, dev: /dev/research/data}
      when: lv is succeeded and 'research' in ansible_facts['lvm']['vgs']
YML
as_student ansible-playbook lv.yml || true
