#!/usr/bin/env bash
# Common mistake: settings without the top-level ansible-navigator key and with the pull policy
# at the wrong level.
student_write ansible-navigator.yml <<YML
---
execution-environment:
  image: $LAB_EE_IMAGE
  pull-policy: $P_POLICY
mode: stdout
playbook-artifact:
  enable: false
YML
