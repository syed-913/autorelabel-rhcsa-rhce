#!/usr/bin/env bash
# Valid alternative: separate tasks with ansible.builtin.replace and an if/else expression.
student_write hwreport.yml <<YML
---
- name: Hardware report
  hosts: all
  tasks:
    - ansible.builtin.get_url:
        url: http://$LAB_UTILITY_FQDN/ansible/files/hwreport.empty
        dest: /root/hwreport.txt
    - ansible.builtin.replace:
        path: /root/hwreport.txt
        regexp: '^HOST=.*$'
        replace: "HOST={{ inventory_hostname }}"
    - ansible.builtin.replace:
        path: /root/hwreport.txt
        regexp: '^MEMORY=.*$'
        replace: "MEMORY={{ ansible_memtotal_mb }}"
    - ansible.builtin.replace:
        path: /root/hwreport.txt
        regexp: '^BIOS=.*$'
        replace: "BIOS={{ ansible_bios_version }}"
    - ansible.builtin.replace:
        path: /root/hwreport.txt
        regexp: '^DISK_{{ item.0 }}_SIZE=.*$'
        replace: "DISK_{{ item.0 }}_SIZE={{ ansible_devices[item.1].size if item.1 in ansible_devices else 'NONE' }}"
      loop: [[A, $LAB_DISK_A], [B, $LAB_DISK_B], [C, $LAB_DISK_C]]
YML
as_student ansible-playbook hwreport.yml
