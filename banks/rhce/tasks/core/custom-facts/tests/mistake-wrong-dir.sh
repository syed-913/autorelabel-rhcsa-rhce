#!/usr/bin/env bash
# Common mistake: the fact file in /etc/ansible/facts (no .d), so ansible_local stays empty.
student_write custom-facts.yml <<YML
---
- name: Install the custom fact
  hosts: dev
  tasks:
    - ansible.builtin.file: {path: /etc/ansible/facts, state: directory}
    - ansible.builtin.copy:
        dest: /etc/ansible/facts/lab.fact
        content: "[service]\nname=$P_SVC\nport=$P_PORT\n"
YML
student_write use-facts.yml <<'YML'
---
- name: Use the custom fact
  hosts: dev
  ignore_errors: true
  tasks:
    - ansible.builtin.copy:
        content: "SERVICE={{ ansible_local['lab']['service']['name'] }} PORT={{ ansible_local['lab']['service']['port'] }}\n"
        dest: /etc/lab-service
YML
as_student ansible-playbook custom-facts.yml
as_student ansible-playbook use-facts.yml || true
