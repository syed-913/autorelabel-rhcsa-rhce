#!/usr/bin/env bash
# Common mistake: webservers lists the prod hosts instead of having prod as a child group.
{
  for g in dev test prod balancers; do
    echo "[$g]"; var="LAB_GROUPS_${g^^}"
    for h in ${!var}; do echo "$h.lab.example.com"; done
  done
  echo "[webservers]"; for h in $LAB_GROUPS_PROD; do echo "$h.lab.example.com"; done
} | student_write inventory
student_write ansible.cfg <<'CFG'
[defaults]
inventory = /home/student/ansible/inventory
remote_user = ansible
roles_path = /home/student/ansible/roles:/usr/share/ansible/roles
collections_path = /home/student/ansible/mycollections:/usr/share/ansible/collections
host_key_checking = False
[privilege_escalation]
become = True
CFG
runuser -u student -- mkdir -p /home/student/ansible/roles /home/student/ansible/mycollections
