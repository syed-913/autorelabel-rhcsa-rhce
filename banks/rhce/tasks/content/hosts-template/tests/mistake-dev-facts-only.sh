#!/usr/bin/env bash
# Common mistake: facts gathered for the dev hosts only, so the other hosts are missing from
# the file (the template skips hosts without facts instead of failing).
student_write templates/hosts.j2 <<'J2'
{% for host in groups['all'] if hostvars[host]['ansible_facts']['fqdn'] is defined %}
{{ hostvars[host]['ansible_facts']['default_ipv4']['address'] }} {{ hostvars[host]['ansible_facts']['fqdn'] }} {{ hostvars[host]['ansible_facts']['hostname'] }}
{% endfor %}
J2
student_write hosts.yml <<'YML'
---
- name: Deploy /etc/myhosts
  hosts: dev
  tasks:
    - ansible.builtin.template: {src: templates/hosts.j2, dest: /etc/myhosts, mode: "0644"}
YML
as_student ansible-playbook hosts.yml
