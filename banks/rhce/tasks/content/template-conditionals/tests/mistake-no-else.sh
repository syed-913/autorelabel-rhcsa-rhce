#!/usr/bin/env bash
# Common mistake: no else branch (other hosts get no Role line) and the list printed as one line.
student_write templates/lab-info.j2 <<'J2'
Host: {{ ansible_facts['hostname'] }}
{% if 'dev' in group_names %}
Role: development
{% elif 'prod' in group_names %}
Role: production
{% endif %}
Contact: {{ lab_contacts | join(', ') }}
J2
student_write lab-info.yml <<'YML'
---
- hosts: all
  vars:
    lab_contacts: [ops@lab.example.com, security@lab.example.com]
  tasks:
    - ansible.builtin.template: {src: templates/lab-info.j2, dest: /etc/lab-info}
YML
as_student ansible-playbook lab-info.yml
