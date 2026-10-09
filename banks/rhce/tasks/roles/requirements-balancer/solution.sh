#!/usr/bin/env bash
student_write roles/requirements.yml <<YML
---
- src: $LAB_ROLES_URL/lab_webserver.tar.gz
  name: webserver
- src: $LAB_ROLES_URL/lab_balancer.tar.gz
  name: balancer
YML
as_student ansible-galaxy role install -r roles/requirements.yml -p roles
student_write roles.yml <<'YML'
---
- name: Web servers
  hosts: webservers
  roles:
    - role: webserver
      webserver_content: "Served by {{ ansible_facts['hostname'] }}"

- name: Load balancers
  hosts: balancers
  roles:
    - balancer
YML
as_student ansible-playbook roles.yml
