#!/usr/bin/env bash
student_write templates/hosts.j2 <<'J2'
{% for host in groups['all'] %}
{{ hostvars[host]['ansible_facts']['default_ipv4']['address'] }} {{ hostvars[host]['ansible_facts']['fqdn'] }} {{ hostvars[host]['ansible_facts']['hostname'] }}
{% endfor %}
J2
student_write hosts.yml <<'YML'
---
- name: Gather facts from every host
  hosts: all
  tasks: []

- name: Deploy /etc/myhosts
  hosts: dev
  tasks:
    - name: Template
      ansible.builtin.template:
        src: templates/hosts.j2
        dest: /etc/myhosts
        owner: root
        mode: "0644"
YML
as_student ansible-playbook hosts.yml
