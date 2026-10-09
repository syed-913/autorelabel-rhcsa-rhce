#!/usr/bin/env bash
# Common mistake: only the new inventory is configured, so the original groups disappear.
student_write "inventory-$P_ZONE.yml" <<YML
---
$P_ZONE:
  hosts:
$(for h in $LAB_GROUPS_BALANCERS; do echo "    $h.lab.example.com:"; done)
  vars:
    zone: $P_ZONE
YML
student_write ansible-navigator.yml <<YML
---
ansible-navigator:
  ansible:
    inventory:
      entries:
        - /home/student/ansible/inventory-$P_ZONE.yml
  execution-environment:
    image: $LAB_EE_IMAGE
    pull:
      policy: missing
  mode: stdout
YML
as_student bash -c 'ansible-navigator inventory --graph > inventory-graph.txt'
