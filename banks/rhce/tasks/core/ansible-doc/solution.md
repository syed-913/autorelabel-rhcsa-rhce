## Finding module options in the documentation

```bash
ansible-doc ansible.posix.sysctl            # full documentation, with EXAMPLES at the end
ansible-doc -s ansible.posix.sysctl         # short snippet of all options
ansible-navigator doc ansible.posix.sysctl -m stdout
ansible-doc -l ansible.posix                # every module in a collection
```

The option is **`sysctl_file`** (default `/etc/sysctl.conf`):

```yaml
---
- name: Kernel parameter
  hosts: all
  tasks:
    - ansible.posix.sysctl:
        name: {{kp.key}}
        value: "{{kp.value}}"
        sysctl_file: /etc/sysctl.d/90-lab.conf
        reload: true                 # apply now (sysctl -p <file>)
```

References: `ansible-doc ansible.posix.sysctl`; `man sysctl.d`.
