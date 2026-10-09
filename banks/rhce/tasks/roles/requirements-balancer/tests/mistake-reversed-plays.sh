#!/usr/bin/env bash
# Common mistake: the balancer play first, before the web servers exist and with no facts
# gathered for them; and the default page content.
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
- hosts: balancers
  roles: [balancer]
- hosts: webservers
  roles: [webserver]
YML
as_student ansible-playbook roles.yml || true
