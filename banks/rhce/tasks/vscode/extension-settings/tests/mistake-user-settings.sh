#!/usr/bin/env bash
# Common mistake: the settings saved as *user* settings (every workspace), not for this workspace.
d=/home/student/.local/share/code-server/User
runuser -u student -- mkdir -p "$d"
cat > "$d/settings.json" <<JSON
{
    "ansible.executionEnvironment.enabled": true,
    "ansible.executionEnvironment.image": "$LAB_EE_IMAGE",
    "ansible.executionEnvironment.containerEngine": "podman",
    "ansible.executionEnvironment.pull.policy": "missing",
    "ansible.ansibleNavigator.path": "/usr/local/bin/ansible-navigator"
}
JSON
chown student:student "$d/settings.json"
student_write ansible-navigator.yml <<YML
---
ansible-navigator:
  execution-environment:
    image: $LAB_EE_IMAGE
    pull:
      policy: missing
YML
