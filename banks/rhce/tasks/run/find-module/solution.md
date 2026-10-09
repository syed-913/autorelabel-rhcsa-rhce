## Discovering a module

```bash
ansible-navigator collections -m stdout                       # what is installed
ansible-navigator doc -l community.general -m stdout | grep -i kernel
ansible-navigator doc community.general.modprobe -m stdout     # options + examples
```

(`ansible-doc -l community.general` and `ansible-doc community.general.modprobe` work as well.)

```yaml
---
- name: Kernel module
  hosts: dev
  tasks:
    - community.general.modprobe:
        name: dummy
        params: numdummies={{num}}
        state: present
        persistent: present      # writes /etc/modules-load.d/dummy.conf and /etc/modprobe.d/dummy.conf
```

`persistent` defaults to `disabled`: the module would be gone after a reboot.

References: `ansible-doc community.general.modprobe`; `man modules-load.d`, `man modprobe.d`.
