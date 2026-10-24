#!/usr/bin/env bash
# Valid alternative: a YAML inventory (same file name) and a minimal ansible.cfg that relies
# on the defaults for become_method/become_user.
{
  echo "all:"; echo "  children:"
  for g in dev test prod balancers; do
    echo "    $g:"; echo "      hosts:"
    var="LAB_GROUPS_${g^^}"
    for h in ${!var}; do echo "        $h.lab.example.com:"; done
  done
  printf '    webservers:\n      children:\n        prod:\n'
} | student_write inventory
student_write ansible.cfg <<'CFG'
[defaults]
inventory=./inventory
remote_user=ansible
roles_path=/home/student/ansible/roles:/usr/share/ansible/roles
collections_path=./mycollections:/usr/share/ansible/collections
host_key_checking=false
[privilege_escalation]
become=true
CFG
runuser -u student -- mkdir -p /home/student/ansible/roles /home/student/ansible/mycollections
