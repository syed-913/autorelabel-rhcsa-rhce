#!/usr/bin/env bash
# Common mistake: firewall rule only at runtime (lost after reboot) and a hard-coded page.
runuser -u student -- mkdir -p /home/student/ansible/roles/apache/tasks /home/student/ansible/roles/apache/templates
student_write roles/apache/tasks/main.yml <<'YML'
---
- ansible.builtin.dnf: {name: [httpd, firewalld]}
- ansible.builtin.service: {name: "{{ item }}", state: started, enabled: true}
  loop: [httpd, firewalld]
- ansible.posix.firewalld: {service: http, immediate: true, state: enabled}
- ansible.builtin.template: {src: index.html.j2, dest: /var/www/html/index.html}
YML
student_write roles/apache/templates/index.html.j2 <<'J2'
Welcome to {{ inventory_hostname }} on {{ ansible_facts['default_ipv4']['address'] }}
J2
student_write apache.yml <<'YML'
---
- hosts: webservers
  roles: [apache]
YML
as_student ansible-playbook apache.yml
