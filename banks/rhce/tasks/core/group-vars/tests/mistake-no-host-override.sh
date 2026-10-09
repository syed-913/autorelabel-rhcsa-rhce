#!/usr/bin/env bash
# Common mistake: the node3 override set as a group variable of prod (it is lost).
student_write group_vars/dev.yml <<<"$P_VAR: development"
student_write group_vars/test.yml <<<"$P_VAR: testing"
student_write group_vars/prod.yml <<<"$P_VAR: production-primary"
runuser -u student -- mkdir -p /home/student/ansible/host_vars
student_write environment.yml <<YML
---
- name: Record the environment
  hosts: dev,test,prod
  tasks:
    - name: Write /etc/lab-environment
      ansible.builtin.copy:
        content: "ENVIRONMENT={{ $P_VAR }}\n"
        dest: /etc/lab-environment
YML
as_student ansible-playbook environment.yml
