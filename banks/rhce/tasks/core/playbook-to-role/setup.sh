#!/usr/bin/env bash
student_write templates/banner.j2 <<'J2'
{{ banner_text }}
J2
student_write banner-legacy.yml <<'YML'
---
- name: Login banner (legacy playbook)
  hosts: test
  vars:
    banner_text: Managed by the lab automation team
  tasks:
    - name: Banner directory
      ansible.builtin.file:
        path: /etc/issue.d
        state: directory
        mode: "0755"
    - name: Banner
      ansible.builtin.template:
        src: templates/banner.j2
        dest: /etc/issue.d/lab-banner.issue
        mode: "0644"
      notify: Record the update
  handlers:
    - name: Record the update
      ansible.builtin.file:
        path: /var/lib/lab-banner/updated
        state: touch
        mode: "0644"
YML
