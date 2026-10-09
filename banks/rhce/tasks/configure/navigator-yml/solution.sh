#!/usr/bin/env bash
student_write ansible-navigator.yml <<YML
---
ansible-navigator:
  execution-environment:
    image: $LAB_EE_IMAGE
    pull:
      policy: $P_POLICY
  mode: stdout
  playbook-artifact:
    enable: false
YML
