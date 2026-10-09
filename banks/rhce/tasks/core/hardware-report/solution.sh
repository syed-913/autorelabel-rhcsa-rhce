#!/usr/bin/env bash
student_write hwreport.yml <<YML
---
- name: Hardware report
  hosts: all
  tasks:
    - name: Download the empty report
      ansible.builtin.get_url:
        url: http://$LAB_UTILITY_FQDN/ansible/files/hwreport.empty
        dest: /root/hwreport.txt
        force: true
        mode: "0644"

    - name: Fill in the values
      ansible.builtin.lineinfile:
        path: /root/hwreport.txt
        regexp: "^{{ item.key }}="
        line: "{{ item.key }}={{ item.value }}"
      loop:
        - { key: HOST, value: "{{ inventory_hostname }}" }
        - { key: MEMORY, value: "{{ ansible_facts['memtotal_mb'] }}" }
        - { key: BIOS, value: "{{ ansible_facts['bios_version'] }}" }
        - { key: DISK_A_SIZE, value: "{{ ansible_facts['devices']['$LAB_DISK_A']['size'] | default('NONE') }}" }
        - { key: DISK_B_SIZE, value: "{{ ansible_facts['devices']['$LAB_DISK_B']['size'] | default('NONE') }}" }
        - { key: DISK_C_SIZE, value: "{{ ansible_facts['devices']['$LAB_DISK_C']['size'] | default('NONE') }}" }
YML
as_student ansible-playbook hwreport.yml
