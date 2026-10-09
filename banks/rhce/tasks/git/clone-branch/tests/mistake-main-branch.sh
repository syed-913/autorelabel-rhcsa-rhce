#!/usr/bin/env bash
# Common mistake: deploying from the default branch (main) without switching to release.
helper="!f() { echo username=student; echo password=$AR_STUDENT_PASSWORD; }; f"
as_student git -c credential.helper="$helper" clone -q "$LAB_GIT_CONTENT_URL" /home/student/lab-content
student_write content.yml <<'YML'
---
- hosts: dev
  tasks:
    - ansible.builtin.file: {path: /srv/lab-content, state: directory}
    - ansible.builtin.copy: {src: /home/student/lab-content/site/index.html, dest: /srv/lab-content/index.html}
YML
as_student ansible-playbook content.yml
