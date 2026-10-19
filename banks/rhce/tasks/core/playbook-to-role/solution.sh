#!/usr/bin/env bash
student_write roles/lab_banner/defaults/main.yml <<'YML'
---
banner_text: Managed by the lab automation team
YML
student_write roles/lab_banner/templates/banner.j2 <<'J2'
{{ banner_text }}
J2
student_write roles/lab_banner/tasks/main.yml <<'YML'
---
- name: Banner directory
  ansible.builtin.file:
    path: /etc/issue.d
    state: directory
    mode: "0755"
- name: Banner
  ansible.builtin.template:
    src: banner.j2
    dest: /etc/issue.d/lab-banner.issue
    mode: "0644"
  notify: Record the update
YML
student_write roles/lab_banner/handlers/main.yml <<'YML'
---
- name: Record the update
  ansible.builtin.file:
    path: /var/log/lab-banner.updated
    state: touch
    mode: "0644"
YML
student_write banner.yml <<YML
---
- name: Login banner
  hosts: test
  roles:
    - role: lab_banner
      banner_text: $P_TEXT
YML
as_student ansible-playbook banner.yml
