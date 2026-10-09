## Services, masking and the default target

```yaml
---
- name: Services
  hosts: test
  tasks:
    - ansible.builtin.dnf:
        name: {{svc}}                      # nfs-server comes from nfs-utils
    - ansible.builtin.systemd_service:
        name: {{svc}}
        state: started
        enabled: true
    - ansible.builtin.systemd_service:
        name: debug-shell.service
        masked: true                        # can't be started at all, even manually
    - ansible.builtin.file:                 # what "systemctl set-default" does
        src: /usr/lib/systemd/system/multi-user.target
        dest: /etc/systemd/system/default.target
        state: link
```

(`ansible.builtin.command: systemctl set-default multi-user.target` works too, with
`changed_when` to keep it honest.)

References: `ansible-doc ansible.builtin.systemd_service`.
