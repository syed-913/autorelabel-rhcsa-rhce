#!/usr/bin/env bash
# Common mistake: banner_text in vars/main.yml instead of defaults/main.yml, and the handler
# left out of the role.
student_write roles/lab_banner/vars/main.yml <<<'banner_text: Managed by the lab automation team'
student_write roles/lab_banner/templates/banner.j2 <<<'{{ banner_text }}'
student_write roles/lab_banner/tasks/main.yml <<'YML'
---
- ansible.builtin.file: {path: /etc/issue.d, state: directory}
- ansible.builtin.template: {src: banner.j2, dest: /etc/issue.d/lab-banner.issue}
YML
student_write banner.yml <<YML
---
- hosts: test
  roles:
    - role: lab_banner
      banner_text: $P_TEXT
YML
as_student ansible-playbook banner.yml
