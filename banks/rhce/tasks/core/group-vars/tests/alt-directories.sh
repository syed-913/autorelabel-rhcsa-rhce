#!/usr/bin/env bash
# Valid alternative: group_vars/<group>/ directories and a template.
student_write group_vars/dev/main.yml <<<"$P_VAR: development"
student_write group_vars/test/vars.yml <<<"$P_VAR: testing"
student_write group_vars/prod/env.yml <<<"$P_VAR: production"
student_write host_vars/node3.lab.example.com/main.yml <<<"$P_VAR: production-primary"
student_write templates/env.j2 <<<"ENVIRONMENT={{ $P_VAR }}"
student_write environment.yml <<YML
---
- name: Record the environment
  hosts: dev:test:prod
  tasks:
    - name: Write /etc/lab-environment
      ansible.builtin.template:
        src: templates/env.j2
        dest: /etc/lab-environment
YML
as_student ansible-playbook environment.yml
