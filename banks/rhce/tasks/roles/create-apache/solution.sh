#!/usr/bin/env bash
as_student ansible-galaxy role init --init-path roles apache >/dev/null
student_write roles/apache/tasks/main.yml <<'YML'
---
- name: Packages
  ansible.builtin.dnf:
    name: [httpd, firewalld]
    state: present
- name: Services
  ansible.builtin.service:
    name: "{{ item }}"
    state: started
    enabled: true
  loop: [httpd, firewalld]
- name: Firewall
  ansible.posix.firewalld:
    service: http
    permanent: true
    immediate: true
    state: enabled
- name: Start page
  ansible.builtin.template:
    src: index.html.j2
    dest: /var/www/html/index.html
    mode: "0644"
YML
student_write roles/apache/templates/index.html.j2 <<'J2'
Welcome to {{ ansible_facts['fqdn'] }} on {{ ansible_facts['default_ipv4']['address'] }}
J2
student_write apache.yml <<'YML'
---
- name: Web servers
  hosts: webservers
  roles:
    - apache
YML
as_student ansible-playbook apache.yml
