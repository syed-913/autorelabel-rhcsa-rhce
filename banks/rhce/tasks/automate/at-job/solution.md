## Finding and using ansible.posix.at

```bash
ansible-navigator collections -m stdout                      # ansible.posix is listed
ansible-navigator doc -l ansible.posix -m stdout | grep -i 'at '
ansible-navigator doc ansible.posix.at -m stdout             # command, count, units, unique
```

```yaml
---
- name: One-time job
  hosts: dev
  tasks:
    - ansible.builtin.dnf:
        name: at
    - ansible.builtin.service:
        name: atd
        state: started
        enabled: true
    - ansible.posix.at:
        command: logger lab-at-{{word}}
        count: {{days}}
        units: days
        unique: true          # don't queue it again on the next run
```

Check on a node with `atq` (the queue) and `at -c <job number>` (the job's script). Jobs are kept
in `/var/spool/at` and survive a reboot; `atd` runs them when they are due.

References: `ansible-doc ansible.posix.at`; `man at`.
