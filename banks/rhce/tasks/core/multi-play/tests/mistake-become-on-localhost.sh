#!/usr/bin/env bash
# Common mistake: the second play inherits become from ansible.cfg (the file belongs to root),
# and the firewall rule is only applied at runtime.
student_write web-site.yml <<'YML'
---
- name: Web servers
  hosts: webservers
  tasks:
    - ansible.builtin.dnf: {name: httpd}
    - ansible.builtin.copy:
        content: "Served by {{ ansible_facts['hostname'] }}\n"
        dest: /var/www/html/index.html
    - ansible.builtin.service: {name: httpd, state: started, enabled: true}
    - ansible.posix.firewalld: {service: http, immediate: true, state: enabled}
- name: Check
  hosts: localhost
  tasks:
    - ansible.builtin.uri: {url: "http://{{ item }}/", return_content: true}
      loop: "{{ groups['webservers'] }}"
      register: pages
    - ansible.builtin.copy:
        content: "{{ pages.results | map(attribute='content') | join('') }}"
        dest: /home/student/ansible/web-check.txt
YML
as_student ansible-playbook web-site.yml || true    # the localhost play fails: sudo wants a password
