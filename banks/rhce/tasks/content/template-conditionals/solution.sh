#!/usr/bin/env bash
student_write templates/lab-info.j2 <<'J2'
Host: {{ ansible_facts['hostname'] }}
{% if 'dev' in group_names %}
Role: development
{% elif 'prod' in group_names %}
Role: production
{% else %}
Role: other
{% endif %}
{% for contact in lab_contacts %}
Contact: {{ contact }}
{% endfor %}
J2
student_write lab-info.yml <<'YML'
---
- name: Lab information
  hosts: all
  vars:
    lab_contacts:
      - ops@lab.example.com
      - security@lab.example.com
  tasks:
    - name: /etc/lab-info
      ansible.builtin.template:
        src: templates/lab-info.j2
        dest: /etc/lab-info
        mode: "0644"
YML
as_student ansible-playbook lab-info.yml
