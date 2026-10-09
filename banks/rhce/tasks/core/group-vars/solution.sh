#!/usr/bin/env bash
student_write group_vars/dev.yml <<<"$P_VAR: development"
student_write group_vars/test.yml <<<"$P_VAR: testing"
student_write group_vars/prod.yml <<<"$P_VAR: production"
student_write host_vars/node3.lab.example.com.yml <<<"$P_VAR: production-primary"
student_write environment.yml <<YML
---
- name: Record the environment
  hosts: dev,test,prod
  tasks:
    - name: Write /etc/lab-environment
      ansible.builtin.copy:
        content: "ENVIRONMENT={{ $P_VAR }}\n"
        dest: /etc/lab-environment
        mode: "0644"
YML
as_student ansible-playbook environment.yml
