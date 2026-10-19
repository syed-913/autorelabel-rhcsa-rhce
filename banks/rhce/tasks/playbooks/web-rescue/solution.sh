#!/usr/bin/env bash
student_write web-deploy.yml <<'YML'
---
- name: Deploy the web servers
  hosts: dev,webservers
  tasks:
    - name: Web server
      block:
        - name: Install httpd
          ansible.builtin.dnf:
            name: httpd
            state: present
        - name: Start page
          ansible.builtin.copy:
            content: "Welcome to {{ ansible_facts['hostname'] }}\n"
            dest: /var/www/html/index.html
            mode: "0644"
        - name: Start and enable httpd
          ansible.builtin.service:
            name: httpd
            state: started
            enabled: true
      rescue:
        - name: Record the error
          ansible.builtin.copy:
            content: "{{ ansible_failed_result.msg }}\n"
            dest: /root/web-failed.txt
            mode: "0644"
        - name: Leave httpd off
          ansible.builtin.service:
            name: httpd
            state: stopped
            enabled: false
      always:
        - name: Trace
          ansible.builtin.copy:
            content: "attempted\n"
            dest: /root/web-attempted.txt
            mode: "0644"
YML
as_student ansible-playbook web-deploy.yml
