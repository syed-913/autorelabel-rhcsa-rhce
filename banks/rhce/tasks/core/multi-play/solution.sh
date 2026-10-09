#!/usr/bin/env bash
student_write web-site.yml <<'YML'
---
- name: Web servers
  hosts: webservers
  tasks:
    - name: Install httpd
      ansible.builtin.dnf:
        name: httpd
        state: present
    - name: Start page
      ansible.builtin.copy:
        content: "Served by {{ ansible_facts['hostname'] }}\n"
        dest: /var/www/html/index.html
        mode: "0644"
    - name: Start and enable httpd
      ansible.builtin.service:
        name: httpd
        state: started
        enabled: true
    - name: Allow http
      ansible.posix.firewalld:
        service: http
        permanent: true
        immediate: true
        state: enabled

- name: Check the web servers from the control node
  hosts: localhost
  become: false
  gather_facts: false
  tasks:
    - name: Fetch every start page
      ansible.builtin.uri:
        url: "http://{{ item }}/"
        return_content: true
      loop: "{{ groups['webservers'] }}"
      register: pages
    - name: Save the responses
      ansible.builtin.copy:
        content: "{{ pages.results | map(attribute='content') | join('') }}"
        dest: /home/student/ansible/web-check.txt
YML
as_student ansible-playbook web-site.yml
