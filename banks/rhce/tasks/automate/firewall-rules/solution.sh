#!/usr/bin/env bash
student_write firewall.yml <<YML
---
- name: Firewall
  hosts: dev
  tasks:
    - name: firewalld
      ansible.builtin.service:
        name: firewalld
        state: started
        enabled: true
    - name: Service
      ansible.posix.firewalld:
        service: $P_SVC
        permanent: true
        immediate: true
        state: enabled
    - name: Port
      ansible.posix.firewalld:
        port: $P_PORT/tcp
        permanent: true
        immediate: true
        state: enabled
    - name: Rich rule
      ansible.posix.firewalld:
        rich_rule: 'rule family="ipv4" source address="$LAB_UTILITY_IP" port port="$P_RPORT" protocol="tcp" accept'
        permanent: true
        immediate: true
        state: enabled
YML
as_student ansible-playbook firewall.yml
