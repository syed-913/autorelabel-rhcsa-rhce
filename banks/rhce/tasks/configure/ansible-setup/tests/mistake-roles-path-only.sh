#!/usr/bin/env bash
# Common mistake: roles_path without /usr/share/ansible/roles (system roles are no longer found).
{
  for g in dev test prod balancers; do
    echo "[$g]"; var="LAB_GROUPS_${g^^}"
    for h in ${!var}; do echo "$h.lab.example.com"; done
  done
  printf '[webservers:children]\nprod\n'
} | student_write inventory
student_write ansible.cfg <<'CFG'
[defaults]
inventory = /home/student/ansible/inventory
remote_user = ansible
roles_path = /home/student/ansible/roles
collections_path = /home/student/ansible/mycollections
host_key_checking = False
[privilege_escalation]
become = True
CFG
runuser -u student -- mkdir -p /home/student/ansible/roles /home/student/ansible/mycollections
