## From playbook to role

```text
roles/lab_banner/
├── defaults/main.yml      banner_text: Managed by the lab automation team
├── handlers/main.yml      - name: Record the update ...
├── tasks/main.yml         the two tasks (template src: banner.j2, no templates/ prefix)
└── templates/banner.j2    {{ banner_text }}
```

`ansible-galaxy role init roles/lab_banner` creates the skeleton (delete what you don't use).

```yaml
---
- name: Login banner
  hosts: test
  roles:
    - role: lab_banner
      banner_text: {{text}}      # role parameter: overrides the role default
```

Role **defaults** have the lowest precedence of all variables, which is exactly why a default is
the right place for a value callers should be able to override. Role `vars/` are much harder to
override. Inside a role, `template: src:` is looked up in the role's `templates/` directory.

References: Ansible docs *Roles*, *Variable precedence*.
