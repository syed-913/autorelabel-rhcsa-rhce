## Running in the development container

```yaml
---
- name: Prove the run happened inside the container
  hosts: dev
  tasks:
    - ansible.builtin.copy:
        content: "{{ lookup('ansible.builtin.env', 'container') }}\n"
        dest: /etc/ee-proof
```

From VS Code's integrated terminal:

```bash
ansible-navigator run ee-proof.yml -m stdout --eei {{lab.ee_image}} --pp missing
```

or enable *Ansible › Execution Environment: Enabled* (image `{{lab.ee_image}}`, engine podman) and
use **Run Ansible Playbook via ansible-navigator** from the editor's context menu.

`lookup()` runs on the controller, which is the container here; podman sets `container=podman`
inside every container, so the file proves where Ansible ran. On the real exam the development
container may be started through VS Code's Dev Containers integration; the idea is the same:
Ansible and its collections come from the container image, not from the host.

References: Ansible VS Code extension documentation; `ansible-navigator run --help`.
