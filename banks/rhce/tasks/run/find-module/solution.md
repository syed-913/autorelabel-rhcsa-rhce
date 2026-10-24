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
        name: brd
        params: rd_nr={{num}}
        state: present
        persistent: present      # writes /etc/modules-load.d/brd.conf and /etc/modprobe.d/brd.conf
```

`persistent` defaults to `disabled`: the module would be gone after a reboot. Check the result
with `cat /sys/module/brd/parameters/rd_nr` and `ls /dev/ram*`, before and after a reboot.

References: `ansible-doc community.general.modprobe`; `man modules-load.d`, `man modprobe.d`.
