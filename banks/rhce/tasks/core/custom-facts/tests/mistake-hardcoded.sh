#!/usr/bin/env bash
# Common mistake: the values typed into the second playbook instead of read from ansible_local.
student_write custom-facts.yml <<YML
---
- name: Install the custom fact
  hosts: dev
  tasks:
    - ansible.builtin.file: {path: /etc/ansible/facts.d, state: directory}
    - ansible.builtin.copy:
        dest: /etc/ansible/facts.d/lab.fact
        content: "[service]\nname=$P_SVC\nport=$P_PORT\n"
YML
student_write use-facts.yml <<YML
---
- name: Use the custom fact
  hosts: dev
  tasks:
    - ansible.builtin.copy:
        content: "SERVICE=$P_SVC PORT=$P_PORT\n"
        dest: /etc/lab-service
YML
as_student ansible-playbook custom-facts.yml
as_student ansible-playbook use-facts.yml
