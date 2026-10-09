## cron with Ansible

```yaml
---
- name: Heartbeat
  hosts: test
  tasks:
    - ansible.builtin.user:
        name: {{user}}
    - ansible.builtin.cron:
        name: lab heartbeat            # Ansible's marker comment; makes the task idempotent
        user: {{user}}
        minute: "*/{{every}}"
        job: logger "EX294 heartbeat"
```

`minute: "{{every}}"` would mean "at minute {{every}} of every hour". Check on a node:
`crontab -l -u {{user}}`.

References: `ansible-doc ansible.builtin.cron`.
