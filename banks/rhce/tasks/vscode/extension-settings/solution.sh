#!/usr/bin/env bash
student_write .vscode/settings.json <<JSON
{
    // Ansible extension: run in the lab execution environment
    "ansible.executionEnvironment.enabled": true,
    "ansible.executionEnvironment.image": "$LAB_EE_IMAGE",
    "ansible.executionEnvironment.containerEngine": "podman",
    "ansible.executionEnvironment.pull.policy": "missing",
    "ansible.ansibleNavigator.path": "/usr/local/bin/ansible-navigator",
}
JSON
student_write ansible-navigator.yml <<YML
---
ansible-navigator:
  execution-environment:
    image: $LAB_EE_IMAGE
    pull:
      policy: missing
YML
