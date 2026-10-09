#!/usr/bin/env bash
student_write custom-facts.yml <<YML
---
- name: Install the custom fact
  hosts: dev
  tasks:
    - name: facts.d directory
      ansible.builtin.file:
        path: /etc/ansible/facts.d
        state: directory
        mode: "0755"
    - name: lab.fact
      ansible.builtin.copy:
        dest: /etc/ansible/facts.d/lab.fact
        content: |
          [service]
          name=$P_SVC
          port=$P_PORT
        mode: "0644"
YML
student_write use-facts.yml <<'YML'
---
- name: Use the custom fact
  hosts: dev
  tasks:
    - name: Write /etc/lab-service
      ansible.builtin.copy:
        content: "SERVICE={{ ansible_local['lab']['service']['name'] }} PORT={{ ansible_local['lab']['service']['port'] }}\n"
        dest: /etc/lab-service
        mode: "0644"
YML
as_student ansible-playbook custom-facts.yml
as_student ansible-playbook use-facts.yml
