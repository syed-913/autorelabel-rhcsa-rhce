#!/usr/bin/env bash
helper="!f() { echo username=student; echo password=$AR_STUDENT_PASSWORD; }; f"
as_student git -c credential.helper="$helper" clone -q "$LAB_GIT_CONTENT_URL" /home/student/lab-content
as_student git -C /home/student/lab-content switch -q release
student_write content.yml <<'YML'
---
- name: Deploy the released content
  hosts: dev
  tasks:
    - name: Directory
      ansible.builtin.file:
        path: /srv/lab-content
        state: directory
        mode: "0755"
    - name: Start page
      ansible.builtin.copy:
        src: /home/student/lab-content/site/index.html
        dest: /srv/lab-content/index.html
        mode: "0644"
YML
as_student ansible-playbook content.yml
