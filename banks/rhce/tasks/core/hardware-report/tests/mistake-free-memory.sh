#!/usr/bin/env bash
# Common mistake: free memory instead of total memory, and no NONE fallback for the third disk.
student_write hwreport.yml <<YML
---
- name: Hardware report
  hosts: all
  ignore_errors: true
  tasks:
    - ansible.builtin.get_url:
        url: http://$LAB_UTILITY_FQDN/ansible/files/hwreport.empty
        dest: /root/hwreport.txt
    - ansible.builtin.lineinfile:
        path: /root/hwreport.txt
        regexp: "^{{ item.key }}="
        line: "{{ item.key }}={{ item.value }}"
      loop:
        - { key: HOST, value: "{{ inventory_hostname }}" }
        - { key: MEMORY, value: "{{ ansible_facts['memfree_mb'] }}" }
        - { key: BIOS, value: "{{ ansible_facts['bios_version'] }}" }
        - { key: DISK_A_SIZE, value: "{{ ansible_facts['devices']['$LAB_DISK_A']['size'] }}" }
        - { key: DISK_B_SIZE, value: "{{ ansible_facts['devices']['$LAB_DISK_B']['size'] }}" }
YML
as_student ansible-playbook hwreport.yml || true
