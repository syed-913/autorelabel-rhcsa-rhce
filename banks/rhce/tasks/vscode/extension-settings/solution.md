## Workspace settings for the Ansible extension

In VS Code: **File → Open Folder** `{{lab.project_dir}}`, then **Settings** (Ctrl+,), switch to the
**Workspace** tab, search for *execution environment* and set the options. VS Code writes them to
`{{lab.project_dir}}/.vscode/settings.json`:

```json
{
    "ansible.executionEnvironment.enabled": true,
    "ansible.executionEnvironment.image": "{{lab.ee_image}}",
    "ansible.executionEnvironment.containerEngine": "podman",
    "ansible.executionEnvironment.pull.policy": "missing",
    "ansible.ansibleNavigator.path": "/usr/local/bin/ansible-navigator"
}
```

The **User** tab would store them in your user profile instead and affect every folder.

`ansible-navigator.yml` for the terminal:

```yaml
---
ansible-navigator:
  execution-environment:
    image: {{lab.ee_image}}
    pull:
      policy: missing
```

References: VS Code docs *User and Workspace Settings*; Ansible VS Code extension documentation.
