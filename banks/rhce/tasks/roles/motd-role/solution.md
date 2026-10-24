## A role from a requirements file, configured through its variables

```yaml
# roles/requirements.yml
---
- src: {{lab.roles_url}}/lab_motd.tar.gz
  name: motd                      # the name it is installed (and used) under
```

```bash
ansible-galaxy role install -r roles/requirements.yml -p roles
cat roles/motd/defaults/main.yml  # motd_message, motd_path: the role's variables
```

```yaml
---
- name: Login notice
  hosts: all
  roles:
    - role: motd
      motd_message: "{{msg}}"
      motd_path: /etc/motd.d/lab-notice
```

A role's `defaults/main.yml` documents what can be changed; its README (when it has one) and
`meta/main.yml` tell more. Role parameters (as above) and play `vars:` both override the
defaults. Messages in `/etc/motd.d/` are shown after `/etc/motd` at login.

References: Ansible docs *Galaxy User Guide* and *Roles*.
