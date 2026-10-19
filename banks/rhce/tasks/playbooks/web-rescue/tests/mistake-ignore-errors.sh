#!/usr/bin/env bash
# Common mistake: ignore_errors instead of a rescue: nothing is recorded and httpd stays enabled.
student_write web-deploy.yml <<'YML'
---
- name: Deploy the web servers
  hosts: dev,webservers
  tasks:
    - ansible.builtin.dnf: {name: httpd}
    - ansible.builtin.copy:
        content: "Welcome to {{ ansible_facts['hostname'] }}\n"
        dest: /var/www/html/index.html
    - ansible.builtin.service: {name: httpd, state: started, enabled: true}
      ignore_errors: true
    - ansible.builtin.copy: {content: "attempted\n", dest: /root/web-attempted.txt}
YML
as_student ansible-playbook web-deploy.yml
